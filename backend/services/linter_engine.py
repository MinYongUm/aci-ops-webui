# ============================================
# ACI Config Linter Engine
# 목적: ACI 설정 데이터에 대한 규칙 평가 엔진
# 버전: v1.3.0
#
# 구조:
#   DataCollector  — imdata 원시 데이터를 클래스별 dict로 정리
#   RuleEngine     — 규칙별 평가 함수 실행 및 결과 수집
#   LintIssue      — 단일 위반 항목 데이터 구조
# ============================================

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ============================================
# 상수 정의
# ============================================

# SEC-001: 위험 키워드 목록 (소문자 비교)
RISKY_CONTRACT_KEYWORDS: list[str] = [
    "permitall",
    "permit_all",
    "allow_all",
    "allowall",
    "any",
]

# NM-001: 이름에 허용되지 않는 문자 패턴 (공백, 특수문자)
# ACI 오브젝트 이름에 허용되는 문자: 영문자, 숫자, 하이픈(-), 밑줄(_), 점(.)
INVALID_NAME_PATTERN: re.Pattern = re.compile(r"[^a-zA-Z0-9\-_.]")

# NM-001 대상 ACI 클래스 목록
NAMING_TARGET_CLASSES: list[str] = [
    "fvTenant",
    "vzBrCP",
    "fvAEPg",
    "fvBD",
    "fvAp",
]


# ============================================
# 데이터 구조 정의
# ============================================


@dataclass
class LintIssue:
    """
    단일 규칙 위반 항목

    Attributes:
        rule_id:   규칙 식별자 (예: SEC-001)
        severity:  위반 심각도 ("critical" or "warning")
        category:  규칙 분류 ("Security", "BestPractice", "Naming")
        dn:        위반 오브젝트의 ACI DN (Distinguished Name)
        message:   위반 사유 설명
    """

    rule_id: str
    severity: str
    category: str
    dn: str
    message: str


@dataclass
class CollectedData:
    """
    DataCollector가 정리한 ACI 클래스별 데이터

    key:   ACI 클래스명 (예: "fvTenant")
    value: 해당 클래스의 attributes 딕셔너리 목록
    """

    objects: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def get(self, class_name: str) -> list[dict[str, Any]]:
        """클래스별 attributes 목록 반환 (없으면 빈 리스트)"""
        return self.objects.get(class_name, [])


# ============================================
# DataCollector
# ============================================


class DataCollector:
    """
    ACI imdata 원시 배열을 클래스별 attributes dict로 정리

    APIC REST API 응답 구조:
        imdata = [
            {"fvTenant": {"attributes": {"name": "...", "dn": "..."}}},
            ...
        ]

    정리 후 구조 (CollectedData.objects):
        {
            "fvTenant": [{"name": "...", "dn": "..."}, ...],
            "vzBrCP":   [{"name": "...", "dn": "..."}, ...],
        }
    """

    @staticmethod
    def from_live(aci_client: Any) -> "CollectedData":
        """
        APIC Live 조회로 데이터 수집

        Args:
            aci_client: ACIClient 인스턴스
        Returns:
            CollectedData
        """
        # 수집 대상 ACI 클래스 목록
        target_classes = [
            "fvTenant",
            "fvAp",
            "fvAEPg",
            "fvBD",
            "fvSubnet",
            "vzBrCP",
            "vzSubj",
            "vzRsSubjFiltAtt",
            "fvRsBd",
            "fvRsProv",
            "fvRsCons",
        ]

        raw: dict[str, list[dict]] = {}

        for class_name in target_classes:
            try:
                imdata = aci_client.get(class_name)
                raw[class_name] = DataCollector._extract_attributes(class_name, imdata)
                logger.debug(
                    "Collected %d objects for class %s",
                    len(raw[class_name]),
                    class_name,
                )
            except Exception as exc:
                logger.warning("Failed to collect class %s: %s", class_name, exc)
                raw[class_name] = []

        collected = CollectedData()
        collected.objects = raw
        return collected

    @staticmethod
    def from_file(file_content: dict) -> "CollectedData":
        """
        업로드된 APIC export JSON 파일에서 데이터 수집

        APIC export 파일 구조:
            {"imdata": [...]}  or  클래스별 배열이 혼합된 구조

        Args:
            file_content: 파싱된 JSON dict
        Returns:
            CollectedData
        """
        imdata: list = []

        # 최상위 imdata 키 존재 여부 확인
        if "imdata" in file_content:
            imdata = file_content["imdata"]
        elif isinstance(file_content, list):
            imdata = file_content
        else:
            logger.warning("Unexpected file structure — no imdata found")

        # 클래스별로 분류
        raw: dict[str, list[dict]] = {}

        for item in imdata:
            if not isinstance(item, dict):
                continue
            for class_name, body in item.items():
                if not isinstance(body, dict):
                    continue
                attrs = body.get("attributes", {})
                if class_name not in raw:
                    raw[class_name] = []
                raw[class_name].append(attrs)

        collected = CollectedData()
        collected.objects = raw
        logger.info("Loaded %d classes from uploaded file", len(raw))
        return collected

    @staticmethod
    def _extract_attributes(class_name: str, imdata: list) -> list[dict[str, Any]]:
        """imdata 배열에서 attributes 딕셔너리만 추출"""
        result = []
        for item in imdata:
            try:
                attrs = item[class_name]["attributes"]
                result.append(attrs)
            except (KeyError, TypeError):
                continue
        return result


# ============================================
# RuleEngine
# ============================================


class RuleEngine:
    """
    규칙 평가 엔진

    각 check_* 메서드가 하나의 규칙에 해당.
    run_all()이 전체 규칙을 순서대로 실행하고 LintIssue 목록을 반환.

    네트워크 비유:
        check_* 함수 = ACL의 개별 라인
        run_all()    = ACL 전체 순차 평가
        LintIssue    = ACL 매칭(히트) 결과
    """

    def __init__(self, naming_config: dict | None = None) -> None:
        """
        Args:
            naming_config: config.yaml의 linter.naming 섹션
                           None이면 기본 규칙(특수문자/공백)만 적용
        """
        self.naming_config: dict = naming_config or {}

    def run_all(self, data: CollectedData) -> list[LintIssue]:
        """
        전체 규칙 실행

        Args:
            data: DataCollector로 정리된 ACI 데이터
        Returns:
            LintIssue 목록
        """
        issues: list[LintIssue] = []

        rule_methods = [
            self.check_sec_001_risky_contract,
            self.check_sec_002_empty_contract,
            self.check_sec_003_empty_subject,
            self.check_bp_001_epg_no_bd,
            self.check_bp_002_epg_no_contract,
            self.check_bp_003_bd_no_subnet,
            self.check_nm_001_invalid_characters,
            self.check_nm_002_prefix_convention,
        ]

        for rule in rule_methods:
            try:
                found = rule(data)
                issues.extend(found)
                logger.debug(
                    "Rule %s: %d issue(s) found",
                    rule.__name__,
                    len(found),
                )
            except Exception as exc:
                logger.error("Rule %s failed: %s", rule.__name__, exc)

        return issues

    # ------------------------------------------
    # Security Rules
    # ------------------------------------------

    def check_sec_001_risky_contract(self, data: CollectedData) -> list[LintIssue]:
        """
        SEC-001: permitAll 계열 위험 키워드를 포함한 Contract 탐지

        탐지 기준: Contract 이름(소문자 변환)에 RISKY_CONTRACT_KEYWORDS 포함
        심각도: critical
        """
        issues: list[LintIssue] = []

        for attrs in data.get("vzBrCP"):
            name: str = attrs.get("name", "")
            dn: str = attrs.get("dn", "")
            name_lower = name.lower()

            for keyword in RISKY_CONTRACT_KEYWORDS:
                if keyword in name_lower:
                    issues.append(
                        LintIssue(
                            rule_id="SEC-001",
                            severity="critical",
                            category="Security",
                            dn=dn,
                            message=(
                                f"Contract '{name}' contains risky keyword "
                                f"'{keyword}' — may allow unrestricted traffic"
                            ),
                        )
                    )
                    break  # 하나의 Contract에 중복 탐지 방지

        return issues

    def check_sec_002_empty_contract(self, data: CollectedData) -> list[LintIssue]:
        """
        SEC-002: Subject가 없는 빈 Contract 탐지

        빈 Contract는 트래픽을 차단하거나 정책 의도가 불명확한 상태.
        Subject DN은 Contract DN을 포함하므로 포함 여부로 판단.

        탐지 기준: Contract의 DN을 포함하는 Subject가 없음
        심각도: warning
        """
        issues: list[LintIssue] = []

        subject_dns: set[str] = {attrs.get("dn", "") for attrs in data.get("vzSubj")}

        for attrs in data.get("vzBrCP"):
            contract_dn: str = attrs.get("dn", "")
            name: str = attrs.get("name", "")

            # Subject DN은 Contract DN을 prefix로 포함
            # 예: uni/tn-T1/brc-CON-Web/subj-Subj1
            has_subject = any(
                subj_dn.startswith(contract_dn + "/") for subj_dn in subject_dns
            )

            if not has_subject:
                issues.append(
                    LintIssue(
                        rule_id="SEC-002",
                        severity="warning",
                        category="Security",
                        dn=contract_dn,
                        message=(
                            f"Contract '{name}' has no Subject — "
                            "traffic policy is undefined"
                        ),
                    )
                )

        return issues

    def check_sec_003_empty_subject(self, data: CollectedData) -> list[LintIssue]:
        """
        SEC-003: Filter가 연결되지 않은 빈 Subject 탐지

        Filter 없는 Subject는 암묵적으로 모든 트래픽을 허용할 수 있음.
        fvRsSubjFiltAtt DN은 Subject DN을 포함.

        탐지 기준: Subject의 DN을 포함하는 fvRsSubjFiltAtt가 없음
        심각도: warning
        """
        issues: list[LintIssue] = []

        filter_att_dns: set[str] = {
            attrs.get("dn", "") for attrs in data.get("vzRsSubjFiltAtt")
        }

        for attrs in data.get("vzSubj"):
            subject_dn: str = attrs.get("dn", "")
            name: str = attrs.get("name", "")

            has_filter = any(
                att_dn.startswith(subject_dn + "/") for att_dn in filter_att_dns
            )

            if not has_filter:
                issues.append(
                    LintIssue(
                        rule_id="SEC-003",
                        severity="warning",
                        category="Security",
                        dn=subject_dn,
                        message=(
                            f"Subject '{name}' has no Filter attached — "
                            "may permit all traffic implicitly"
                        ),
                    )
                )

        return issues

    # ------------------------------------------
    # Best Practice Rules
    # ------------------------------------------

    def check_bp_001_epg_no_bd(self, data: CollectedData) -> list[LintIssue]:
        """
        BP-001: BD가 연결되지 않은 EPG 탐지

        EPG는 반드시 BD에 연결되어야 함.
        fvRsBd DN은 EPG DN을 포함.

        탐지 기준: EPG의 DN을 포함하는 fvRsBd가 없음
        심각도: critical
        """
        issues: list[LintIssue] = []

        bd_rel_dns: set[str] = {attrs.get("dn", "") for attrs in data.get("fvRsBd")}

        for attrs in data.get("fvAEPg"):
            epg_dn: str = attrs.get("dn", "")
            name: str = attrs.get("name", "")

            has_bd = any(rel_dn.startswith(epg_dn + "/") for rel_dn in bd_rel_dns)

            if not has_bd:
                issues.append(
                    LintIssue(
                        rule_id="BP-001",
                        severity="critical",
                        category="BestPractice",
                        dn=epg_dn,
                        message=(
                            f"EPG '{name}' is not associated with any BD — "
                            "endpoints cannot forward traffic"
                        ),
                    )
                )

        return issues

    def check_bp_002_epg_no_contract(self, data: CollectedData) -> list[LintIssue]:
        """
        BP-002: Contract(Provided/Consumed)이 없는 고립 EPG 탐지

        Contract 미연결 EPG는 다른 EPG와 통신 불가 상태.

        탐지 기준: EPG DN을 포함하는 fvRsProv 또는 fvRsCons가 모두 없음
        심각도: warning
        """
        issues: list[LintIssue] = []

        prov_dns: set[str] = {attrs.get("dn", "") for attrs in data.get("fvRsProv")}
        cons_dns: set[str] = {attrs.get("dn", "") for attrs in data.get("fvRsCons")}

        for attrs in data.get("fvAEPg"):
            epg_dn: str = attrs.get("dn", "")
            name: str = attrs.get("name", "")

            has_prov = any(dn.startswith(epg_dn + "/") for dn in prov_dns)
            has_cons = any(dn.startswith(epg_dn + "/") for dn in cons_dns)

            if not has_prov and not has_cons:
                issues.append(
                    LintIssue(
                        rule_id="BP-002",
                        severity="warning",
                        category="BestPractice",
                        dn=epg_dn,
                        message=(
                            f"EPG '{name}' has no Provided or Consumed Contract — "
                            "isolated from all other EPGs"
                        ),
                    )
                )

        return issues

    def check_bp_003_bd_no_subnet(self, data: CollectedData) -> list[LintIssue]:
        """
        BP-003: Subnet이 없는 BD 탐지

        L3 통신이 필요한 BD에는 Subnet이 설정되어야 함.
        (L2-only BD는 의도적으로 Subnet 없이 사용하는 경우도 있으므로 warning 처리)

        탐지 기준: BD DN을 포함하는 fvSubnet이 없음
        심각도: warning
        """
        issues: list[LintIssue] = []

        subnet_dns: set[str] = {attrs.get("dn", "") for attrs in data.get("fvSubnet")}

        for attrs in data.get("fvBD"):
            bd_dn: str = attrs.get("dn", "")
            name: str = attrs.get("name", "")

            has_subnet = any(sn_dn.startswith(bd_dn + "/") for sn_dn in subnet_dns)

            if not has_subnet:
                issues.append(
                    LintIssue(
                        rule_id="BP-003",
                        severity="warning",
                        category="BestPractice",
                        dn=bd_dn,
                        message=(
                            f"BD '{name}' has no Subnet configured — "
                            "L3 forwarding unavailable (ignore if L2-only)"
                        ),
                    )
                )

        return issues

    # ------------------------------------------
    # Naming Convention Rules
    # ------------------------------------------

    def check_nm_001_invalid_characters(self, data: CollectedData) -> list[LintIssue]:
        """
        NM-001: 이름에 공백 또는 허용되지 않는 특수문자 포함 탐지

        허용 문자: 영문자, 숫자, 하이픈(-), 밑줄(_), 점(.)
        탐지 기준: INVALID_NAME_PATTERN 매칭
        심각도: warning
        """
        issues: list[LintIssue] = []

        for class_name in NAMING_TARGET_CLASSES:
            for attrs in data.get(class_name):
                name: str = attrs.get("name", "")
                dn: str = attrs.get("dn", "")

                if INVALID_NAME_PATTERN.search(name):
                    issues.append(
                        LintIssue(
                            rule_id="NM-001",
                            severity="warning",
                            category="Naming",
                            dn=dn,
                            message=(
                                f"{class_name} '{name}' contains invalid characters — "
                                "allowed: letters, numbers, hyphen, underscore, dot"
                            ),
                        )
                    )

        return issues

    def check_nm_002_prefix_convention(self, data: CollectedData) -> list[LintIssue]:
        """
        NM-002: config.yaml에 정의된 prefix 규칙 위반 탐지

        config.yaml linter.naming 섹션이 비어있으면 이 규칙은 스킵.

        지원 prefix 설정 키:
            tenant_prefix, bd_prefix, epg_prefix,
            contract_prefix, ap_prefix

        심각도: warning
        """
        issues: list[LintIssue] = []

        # config.yaml에 naming 설정이 없으면 스킵
        if not self.naming_config:
            return issues

        # prefix 설정 키 → ACI 클래스 매핑
        prefix_class_map: dict[str, str] = {
            "tenant_prefix": "fvTenant",
            "bd_prefix": "fvBD",
            "epg_prefix": "fvAEPg",
            "contract_prefix": "vzBrCP",
            "ap_prefix": "fvAp",
        }

        for config_key, class_name in prefix_class_map.items():
            required_prefix: str = self.naming_config.get(config_key, "")

            # prefix 미설정 시 해당 클래스 스킵
            if not required_prefix:
                continue

            for attrs in data.get(class_name):
                name: str = attrs.get("name", "")
                dn: str = attrs.get("dn", "")

                if not name.startswith(required_prefix):
                    issues.append(
                        LintIssue(
                            rule_id="NM-002",
                            severity="warning",
                            category="Naming",
                            dn=dn,
                            message=(
                                f"{class_name} '{name}' does not match required prefix "
                                f"'{required_prefix}'"
                            ),
                        )
                    )

        return issues


# ============================================
# LinterService — 외부 인터페이스
# ============================================


class LinterService:
    """
    linter_engine.py의 외부 인터페이스.
    routers/linter.py에서 이 클래스만 import하여 사용.

    사용 예시:
        service = LinterService(config_path="config.yaml")
        result = service.run_live(aci_client)
        result = service.run_from_file(json_content)
    """

    def __init__(self, config_path: str = "config.yaml") -> None:
        self.naming_config: dict = self._load_naming_config(config_path)
        self.engine = RuleEngine(naming_config=self.naming_config)

    def _load_naming_config(self, config_path: str) -> dict:
        """config.yaml에서 linter.naming 섹션 로드"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            naming = config.get("linter", {}).get("naming", {})
            logger.info("Naming config loaded: %s", naming)
            return naming
        except FileNotFoundError:
            logger.warning("config.yaml not found — naming rules will use defaults")
            return {}
        except Exception as exc:
            logger.error("Failed to load naming config: %s", exc)
            return {}

    def run_live(self, aci_client: Any) -> dict:
        """
        APIC Live 조회 후 전체 규칙 실행

        Args:
            aci_client: ACIClient 인스턴스
        Returns:
            결과 dict (API 응답 형식)
        """
        logger.info("Starting live lint scan")
        data = DataCollector.from_live(aci_client)
        return self._build_result(data, source="live")

    def run_from_file(self, file_content: dict) -> dict:
        """
        업로드 파일 기반 전체 규칙 실행

        Args:
            file_content: 파싱된 JSON dict
        Returns:
            결과 dict (API 응답 형식)
        """
        logger.info("Starting file-based lint scan")
        data = DataCollector.from_file(file_content)
        return self._build_result(data, source="upload")

    def _build_result(self, data: CollectedData, source: str) -> dict:
        """규칙 실행 결과를 API 응답 형식으로 변환"""
        issues = self.engine.run_all(data)

        severity_summary = {"critical": 0, "warning": 0}
        for issue in issues:
            if issue.severity in severity_summary:
                severity_summary[issue.severity] += 1

        logger.info(
            "Lint complete — source=%s, total=%d, critical=%d, warning=%d",
            source,
            len(issues),
            severity_summary["critical"],
            severity_summary["warning"],
        )

        return {
            "source": source,
            "total_issues": len(issues),
            "summary": severity_summary,
            "results": [
                {
                    "rule_id": issue.rule_id,
                    "severity": issue.severity,
                    "category": issue.category,
                    "dn": issue.dn,
                    "message": issue.message,
                }
                for issue in issues
            ],
        }
