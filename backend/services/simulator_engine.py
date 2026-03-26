# ============================================
# Microsegmentation Simulator Engine
# 목적: ACI EPG 간 트래픽 허용/차단 시뮬레이션
# 버전: v1.4.0
#
# 판정 기준 (ACI Whitelist 모델):
#   Source EPG (Consumer) + Dest EPG (Provider)가
#   동일 Contract로 연결되어 있고,
#   해당 Contract에 Subject + Filter가 존재하면 ALLOW
#   그 외 모든 경우는 DENY (묵시적 거부)
# ============================================

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================
# 데이터 클래스 정의
# ============================================


@dataclass
class EpgInfo:
    """EPG 기본 정보"""

    dn: str
    name: str
    tenant: str
    app_profile: str


@dataclass
class FilterEntry:
    """Contract Filter 상세 항목"""

    name: str
    ether_type: str = "unspecified"
    ip_protocol: str = "unspecified"
    dst_from_port: str = "unspecified"
    dst_to_port: str = "unspecified"


@dataclass
class SubjectInfo:
    """Contract Subject 정보"""

    name: str
    filters: list[FilterEntry] = field(default_factory=list)


@dataclass
class ContractInfo:
    """Contract 전체 정보"""

    name: str
    tenant: str
    dn: str
    subjects: list[SubjectInfo] = field(default_factory=list)


@dataclass
class SimulationResult:
    """시뮬레이션 결과"""

    verdict: str  # "ALLOW" or "DENY"
    src_epg: str
    dst_epg: str
    src_tenant: str
    dst_tenant: str
    matched_contracts: list[ContractInfo] = field(default_factory=list)
    reason: str = ""


# ============================================
# 헬퍼 함수
# ============================================


def _extract_tenant(dn: str) -> str:
    """DN에서 Tenant 이름 추출. 예: uni/tn-TenantA/... → TenantA"""
    match = re.search(r"tn-([^/]+)", dn)
    return match.group(1) if match else "unknown"


def _extract_contract_name(tdn: str) -> str:
    """tDn에서 Contract 이름 추출. 예: uni/tn-T1/brc-web-to-db → web-to-db"""
    match = re.search(r"brc-([^/]+)", tdn)
    return match.group(1) if match else tdn


def _extract_subject_name(dn: str) -> str:
    """DN에서 Subject 이름 추출. 예: uni/tn-T1/brc-c1/subj-s1 → s1"""
    match = re.search(r"subj-([^/]+)", dn)
    return match.group(1) if match else dn


def _extract_filter_name(tdn: str) -> str:
    """tDn에서 Filter 이름 추출. 예: uni/tn-T1/flt-tcp-80 → tcp-80"""
    match = re.search(r"flt-([^/]+)", tdn)
    return match.group(1) if match else tdn


def _make_contract_key(tenant: str, name: str) -> str:
    """Contract 고유 키 생성 (Tenant 범위 포함)"""
    return f"{tenant}::{name}"


# ============================================
# 데이터 수집 클래스
# ============================================


class SimulatorDataCollector:
    """
    APIC에서 시뮬레이션에 필요한 데이터 수집

    수집 항목:
    - EPG 목록 및 Tenant/AP 정보
    - EPG별 Provider/Consumer Contract 관계
    - Contract → Subject → Filter 체인
    """

    def __init__(self, aci) -> None:
        self._aci = aci

    # ------------------------------------------
    # Public API
    # ------------------------------------------

    def get_tenants(self) -> list[dict]:
        """
        Tenant 목록 반환 (드롭다운용)

        Returns:
            [{"name": "TenantA", "dn": "uni/tn-TenantA"}, ...]
        """
        try:
            raw = self._aci.get("fvTenant")
        except Exception:
            logger.exception("fvTenant 조회 실패")
            return []

        result = []
        for item in raw:
            attr = item["fvTenant"]["attributes"]
            name = attr.get("name", "")
            # 시스템 Tenant 제외
            if name not in ("common", "infra", "mgmt"):
                result.append({"name": name, "dn": attr.get("dn", "")})

        return sorted(result, key=lambda x: x["name"])

    def get_epgs(self, tenant: Optional[str] = None) -> list[EpgInfo]:
        """
        EPG 목록 반환

        Args:
            tenant: Tenant 이름으로 필터링 (None이면 전체)
        Returns:
            EpgInfo 목록
        """
        try:
            raw = self._aci.get("fvAEPg")
        except Exception:
            logger.exception("fvAEPg 조회 실패")
            return []

        result = []
        for item in raw:
            attr = item["fvAEPg"]["attributes"]
            dn = attr.get("dn", "")
            epg_tenant = _extract_tenant(dn)

            if tenant and epg_tenant != tenant:
                continue

            # DN 파싱: uni/tn-T1/ap-App/epg-Web
            ap_match = re.search(r"ap-([^/]+)", dn)
            epg_match = re.search(r"epg-([^/]+)", dn)

            result.append(
                EpgInfo(
                    dn=dn,
                    name=epg_match.group(1) if epg_match else attr.get("name", ""),
                    tenant=epg_tenant,
                    app_profile=ap_match.group(1) if ap_match else "unknown",
                )
            )

        return sorted(result, key=lambda x: (x.tenant, x.app_profile, x.name))

    def collect_all(self) -> dict:
        """
        시뮬레이션 판정에 필요한 전체 데이터 수집

        Returns:
            {
                "epgs": list[EpgInfo],
                "providers": dict[epg_dn → list[contract_key]],
                "consumers": dict[epg_dn → list[contract_key]],
                "contracts": dict[contract_key → ContractInfo]
            }
        """
        logger.info("시뮬레이션 데이터 수집 시작")

        epgs = self.get_epgs()

        # EPG → Provider Contract 관계
        providers: dict[str, list[str]] = {}
        try:
            for item in self._aci.get("fvRsProv"):
                attr = item["fvRsProv"]["attributes"]
                epg_dn = re.sub(r"/rsprov-[^/]+$", "", attr.get("dn", ""))
                tenant = _extract_tenant(epg_dn)
                contract_name = _extract_contract_name(attr.get("tnVzBrCPName", ""))
                key = _make_contract_key(tenant, contract_name)
                providers.setdefault(epg_dn, []).append(key)
        except Exception:
            logger.exception("fvRsProv 조회 실패")

        # EPG → Consumer Contract 관계
        consumers: dict[str, list[str]] = {}
        try:
            for item in self._aci.get("fvRsCons"):
                attr = item["fvRsCons"]["attributes"]
                epg_dn = re.sub(r"/rscons-[^/]+$", "", attr.get("dn", ""))
                tenant = _extract_tenant(epg_dn)
                contract_name = _extract_contract_name(attr.get("tnVzBrCPName", ""))
                key = _make_contract_key(tenant, contract_name)
                consumers.setdefault(epg_dn, []).append(key)
        except Exception:
            logger.exception("fvRsCons 조회 실패")

        # Contract → Subject 매핑
        subj_map: dict[str, list[str]] = {}  # contract_dn → [subject_dn, ...]
        try:
            for item in self._aci.get("vzSubj"):
                attr = item["vzSubj"]["attributes"]
                dn = attr.get("dn", "")
                # contract DN: uni/tn-T1/brc-c1/subj-s1 → uni/tn-T1/brc-c1
                contract_dn = re.sub(r"/subj-[^/]+$", "", dn)
                subj_map.setdefault(contract_dn, []).append(dn)
        except Exception:
            logger.exception("vzSubj 조회 실패")

        # Subject → Filter 매핑
        filter_map: dict[str, list[str]] = {}  # subject_dn → [filter_name, ...]
        try:
            for item in self._aci.get("vzRsSubjFiltAtt"):
                attr = item["vzRsSubjFiltAtt"]["attributes"]
                dn = attr.get("dn", "")
                subj_dn = re.sub(r"/rssubjFiltAtt-[^/]+$", "", dn)
                filter_name = _extract_filter_name(attr.get("tnVzFilterName", ""))
                filter_map.setdefault(subj_dn, []).append(filter_name)
        except Exception:
            logger.exception("vzRsSubjFiltAtt 조회 실패")

        # Contract 조합
        contracts: dict[str, ContractInfo] = {}
        try:
            for item in self._aci.get("vzBrCP"):
                attr = item["vzBrCP"]["attributes"]
                dn = attr.get("dn", "")
                tenant = _extract_tenant(dn)
                name = attr.get("name", "")
                key = _make_contract_key(tenant, name)

                subjects = []
                for subj_dn in subj_map.get(dn, []):
                    subj_name = _extract_subject_name(subj_dn)
                    filter_names = filter_map.get(subj_dn, [])
                    subjects.append(
                        SubjectInfo(
                            name=subj_name,
                            filters=[FilterEntry(name=f) for f in filter_names],
                        )
                    )

                contracts[key] = ContractInfo(
                    name=name, tenant=tenant, dn=dn, subjects=subjects
                )
        except Exception:
            logger.exception("vzBrCP 조회 실패")

        logger.info(
            "데이터 수집 완료 — EPG: %d, Contract: %d", len(epgs), len(contracts)
        )

        return {
            "epgs": epgs,
            "providers": providers,
            "consumers": consumers,
            "contracts": contracts,
        }


# ============================================
# 시뮬레이션 엔진
# ============================================


class SimulatorEngine:
    """
    Microsegmentation 시뮬레이션 엔진

    ACI Whitelist 모델 기준:
    - EPG 간 통신은 기본 Deny-All
    - Consumer → Provider 방향으로 Contract가 연결되어 있고
      해당 Contract에 Subject + Filter가 존재해야 ALLOW
    """

    def __init__(self, aci) -> None:
        self._collector = SimulatorDataCollector(aci)

    def get_tenants(self) -> list[dict]:
        """Tenant 목록 반환 (UI 드롭다운용)"""
        return self._collector.get_tenants()

    def get_epgs(self, tenant: Optional[str] = None) -> list[dict]:
        """
        EPG 목록 반환 (UI 드롭다운용)

        Returns:
            [{"dn": ..., "name": ..., "tenant": ..., "app_profile": ...}, ...]
        """
        epgs = self._collector.get_epgs(tenant)
        return [
            {
                "dn": e.dn,
                "name": e.name,
                "tenant": e.tenant,
                "app_profile": e.app_profile,
                "display": f"{e.app_profile} / {e.name}",
            }
            for e in epgs
        ]

    def simulate(self, src_epg_dn: str, dst_epg_dn: str) -> SimulationResult:
        """
        트래픽 허용/차단 시뮬레이션 실행

        Args:
            src_epg_dn: Source EPG DN (Consumer 역할)
            dst_epg_dn: Destination EPG DN (Provider 역할)
        Returns:
            SimulationResult
        """
        data = self._collector.collect_all()

        # EPG 정보 조회
        epg_map: dict[str, EpgInfo] = {e.dn: e for e in data["epgs"]}
        src_info = epg_map.get(src_epg_dn)
        dst_info = epg_map.get(dst_epg_dn)

        # DN이 조회 목록에 없는 경우 DN에서 직접 파싱
        if not src_info:
            src_info = _epg_info_from_dn(src_epg_dn)
        if not dst_info:
            dst_info = _epg_info_from_dn(dst_epg_dn)

        src_label = f"{src_info.tenant} / {src_info.app_profile} / {src_info.name}"
        dst_label = f"{dst_info.tenant} / {dst_info.app_profile} / {dst_info.name}"

        logger.info("시뮬레이션 실행 — SRC: %s → DST: %s", src_label, dst_label)

        # ----------------------------------------
        # 판정 로직
        # Source EPG의 Consumer Contract와
        # Dest EPG의 Provider Contract의 교집합 탐색
        # ----------------------------------------
        src_consumed = set(data["consumers"].get(src_epg_dn, []))
        dst_provided = set(data["providers"].get(dst_epg_dn, []))

        matched_keys = src_consumed & dst_provided

        if not matched_keys:
            return SimulationResult(
                verdict="DENY",
                src_epg=src_info.name,
                dst_epg=dst_info.name,
                src_tenant=src_info.tenant,
                dst_tenant=dst_info.tenant,
                matched_contracts=[],
                reason=(
                    f"No Contract found between "
                    f"'{src_info.name}'(Consumer) and "
                    f"'{dst_info.name}'(Provider). "
                    f"ACI default policy: Deny-All."
                ),
            )

        # 매칭된 Contract 중 Subject + Filter 유효성 확인
        valid_contracts: list[ContractInfo] = []
        empty_contracts: list[ContractInfo] = []

        for key in matched_keys:
            contract = data["contracts"].get(key)
            if not contract:
                continue

            has_filter = any(len(subj.filters) > 0 for subj in contract.subjects)

            if contract.subjects and has_filter:
                valid_contracts.append(contract)
            else:
                empty_contracts.append(contract)

        # 유효 Contract 있음 → ALLOW
        if valid_contracts:
            contract_names = ", ".join(f"'{c.name}'" for c in valid_contracts)
            return SimulationResult(
                verdict="ALLOW",
                src_epg=src_info.name,
                dst_epg=dst_info.name,
                src_tenant=src_info.tenant,
                dst_tenant=dst_info.tenant,
                matched_contracts=valid_contracts,
                reason=(
                    f"Contract {contract_names} permits traffic: "
                    f"'{src_info.name}'(Consumer) → '{dst_info.name}'(Provider)."
                ),
            )

        # Contract은 있으나 Subject/Filter 없음 → DENY
        contract_names = ", ".join(f"'{c.name}'" for c in empty_contracts)
        return SimulationResult(
            verdict="DENY",
            src_epg=src_info.name,
            dst_epg=dst_info.name,
            src_tenant=src_info.tenant,
            dst_tenant=dst_info.tenant,
            matched_contracts=empty_contracts,
            reason=(
                f"Contract {contract_names} exists but has no Subject or Filter. "
                f"Traffic is denied."
            ),
        )


# ============================================
# 헬퍼 — DN으로부터 EpgInfo 생성 (조회 실패 시 폴백)
# ============================================


def _epg_info_from_dn(dn: str) -> EpgInfo:
    """DN 파싱만으로 EpgInfo 구성 (APIC 조회 결과 없을 때 폴백)"""
    tenant = _extract_tenant(dn)
    ap_match = re.search(r"ap-([^/]+)", dn)
    epg_match = re.search(r"epg-([^/]+)", dn)
    return EpgInfo(
        dn=dn,
        name=epg_match.group(1) if epg_match else dn,
        tenant=tenant,
        app_profile=ap_match.group(1) if ap_match else "unknown",
    )
