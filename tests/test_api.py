# ============================================
# ACI Ops WebUI - API Test Suite
# 버전: v1.4.0
# 목적: FastAPI 엔드포인트 단위 테스트 (APIC 미연결 환경)
#
# 실행 방법:
#   cd aci-ops-webui
#   pytest tests/ -v
#
# 주의:
#   - 실제 APIC 접속 없이 동작하도록 ACIClient를 Mock 처리
#   - CI/CD (GitHub Actions) 환경에서 자동 실행됨
# ============================================

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
import requests

import pytest
from fastapi.testclient import TestClient

# backend/ 디렉토리를 기준으로 import
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app  # noqa: E402
from services.simulator_engine import (  # noqa: E402
    ContractInfo,
    FilterEntry,
    SimulationResult,
    SubjectInfo,
)

# ============================================
# Mock 데이터 픽스처
# ============================================

MOCK_HEALTH: dict[str, Any] = {
    "total_faults": 3,
    "nodes": {"up": 4, "down": 0},
    "faults": [
        {
            "severity": "major",
            "description": "Interface Eth1/1 is down",
            "dn": "topology/pod-1/node-101/uni/epp/fv-[uni/tn-TenantA]/node-101/stpathatt-[eth1/1]",
        }
    ],
}

MOCK_POLICY: dict[str, Any] = {
    "security_risks": 1,
    "contracts": [
        {"name": "allow-all", "tenant": "TenantA", "risk": "high"},
    ],
}

MOCK_INTERFACE: dict[str, Any] = {
    "total": 48,
    "up": 32,
    "down": 16,
    "interfaces": [
        {"id": "eth1/1", "node": "101", "state": "up", "speed": "10G"},
    ],
}

MOCK_ENDPOINT: dict[str, Any] = {
    "total": 120,
    "endpoints": [
        {
            "mac": "00:50:56:AA:BB:CC",
            "ip": "10.0.0.1",
            "tenant": "TenantA",
            "epg": "EPG_WEB",
            "node": "101",
            "interface": "eth1/10",
        }
    ],
}

MOCK_AUDIT: dict[str, Any] = {
    "total": 50,
    "logs": [
        {
            "user": "admin",
            "action": "creation",
            "affected_object": "uni/tn-TenantA/ap-APP/epg-EPG_TEST",
            "timestamp": "2026-03-17T09:00:00.000+00:00",
        }
    ],
}

MOCK_CAPACITY: dict[str, Any] = {
    "nodes": [
        {"node": "101", "tcam_usage_pct": 42.5},
        {"node": "102", "tcam_usage_pct": 38.1},
    ]
}

MOCK_TOPOLOGY: dict[str, Any] = {
    "spines": ["spine-201", "spine-202"],
    "leaves": ["leaf-101", "leaf-102", "leaf-103"],
    "links": [
        {"from": "spine-201", "to": "leaf-101"},
        {"from": "spine-201", "to": "leaf-102"},
    ],
}

MOCK_ENDPOINT_SEARCH: list[dict[str, Any]] = [
    {
        "mac": "00:50:56:AA:BB:CC",
        "ip": "10.0.0.1",
        "tenant": "TenantA",
        "epg": "EPG_WEB",
        "node": "101",
        "interface": "eth1/10",
    }
]

# ------------------------------------------
# Simulator Mock 데이터
# ------------------------------------------

MOCK_SIMULATE_ALLOW = SimulationResult(
    verdict="ALLOW",
    src_epg="Web",
    dst_epg="DB",
    src_tenant="TenantA",
    dst_tenant="TenantA",
    matched_contracts=[
        ContractInfo(
            name="web-to-db",
            tenant="TenantA",
            dn="uni/tn-TenantA/brc-web-to-db",
            subjects=[
                SubjectInfo(
                    name="http",
                    filters=[
                        FilterEntry(
                            name="tcp-3306",
                            ether_type="ip",
                            ip_protocol="tcp",
                            dst_from_port="3306",
                            dst_to_port="3306",
                        )
                    ],
                )
            ],
        )
    ],
    reason="Contract 'web-to-db' permits traffic: 'Web'(Consumer) -> 'DB'(Provider).",
)

MOCK_SIMULATE_DENY = SimulationResult(
    verdict="DENY",
    src_epg="Web",
    dst_epg="Infra",
    src_tenant="TenantA",
    dst_tenant="TenantA",
    matched_contracts=[],
    reason="No Contract found between 'Web'(Consumer) and 'Infra'(Provider). ACI default policy: Deny-All.",
)

SRC_EPG_DN = "uni/tn-TenantA/ap-App/epg-Web"
DST_EPG_DN = "uni/tn-TenantA/ap-App/epg-DB"


# ============================================
# 픽스처: Mock ACIClient + TestClient
# ============================================


@pytest.fixture()
def client() -> TestClient:
    """
    FastAPI TestClient 픽스처.

    ACIClient.__init__ 과 ACIClient.login 을 Mock 처리하여
    실제 APIC 접속 없이 테스트가 실행되도록 한다.
    """
    with patch("main.ACIClient") as mock_aci_class:
        mock_aci_instance = MagicMock()
        mock_aci_class.return_value = mock_aci_instance
        mock_aci_instance.get.return_value = []  # Linter/Simulator Live Scan용 빈 배열

        # 각 라우터 함수가 참조하는 데이터 반환값 설정
        with (
            patch("main.get_health_data", return_value=MOCK_HEALTH),
            patch("main.get_policy_data", return_value=MOCK_POLICY),
            patch("main.get_interface_data", return_value=MOCK_INTERFACE),
            patch("main.get_endpoint_data", return_value=MOCK_ENDPOINT),
            patch("main.search_endpoint", return_value=MOCK_ENDPOINT_SEARCH),
            patch("main.get_audit_data", return_value=MOCK_AUDIT),
            patch("main.get_capacity_data", return_value=MOCK_CAPACITY),
            patch("main.get_topology_data", return_value=MOCK_TOPOLOGY),
        ):
            yield TestClient(app)


# ============================================
# 테스트: 루트 엔드포인트
# ============================================


class TestRoot:
    @pytest.mark.skip(
        reason="GET /는 FileResponse(HTML)를 반환하므로 API 테스트 범위 제외"
    )
    def test_root_returns_200(self, client: TestClient) -> None:
        """GET / 가 200을 반환해야 한다."""
        response = client.get("/")
        assert response.status_code == 200


# ============================================
# 테스트: Health Check API
# ============================================


class TestHealthAPI:
    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_contains_total_faults(self, client: TestClient) -> None:
        response = client.get("/api/health")
        data = response.json()
        assert "total_faults" in data

    def test_health_contains_nodes(self, client: TestClient) -> None:
        response = client.get("/api/health")
        data = response.json()
        assert "nodes" in data
        assert "up" in data["nodes"]


# ============================================
# 테스트: Policy Check API
# ============================================


class TestPolicyAPI:
    def test_policy_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/policy")
        assert response.status_code == 200

    def test_policy_contains_security_risks(self, client: TestClient) -> None:
        response = client.get("/api/policy")
        data = response.json()
        assert "security_risks" in data


# ============================================
# 테스트: Interface Monitor API
# ============================================


class TestInterfaceAPI:
    def test_interface_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/interface")
        assert response.status_code == 200

    def test_interface_contains_totals(self, client: TestClient) -> None:
        response = client.get("/api/interface")
        data = response.json()
        assert "total" in data
        assert "up" in data
        assert "down" in data


# ============================================
# 테스트: Endpoint Tracker API
# ============================================


class TestEndpointAPI:
    def test_endpoint_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/endpoint")
        assert response.status_code == 200

    def test_endpoint_contains_total(self, client: TestClient) -> None:
        response = client.get("/api/endpoint")
        data = response.json()
        assert "total" in data

    def test_endpoint_search_with_mac(self, client: TestClient) -> None:
        """MAC 주소로 Endpoint 검색 시 결과를 반환해야 한다."""
        response = client.get("/api/endpoint/search?q=00:50:56:AA:BB:CC")
        assert response.status_code == 200

    def test_endpoint_search_with_ip(self, client: TestClient) -> None:
        """IP 주소로 Endpoint 검색 시 결과를 반환해야 한다."""
        response = client.get("/api/endpoint/search?q=10.0.0.1")
        assert response.status_code == 200

    def test_endpoint_search_missing_query_returns_422(
        self, client: TestClient
    ) -> None:
        """검색어(q) 파라미터 누락 시 422 Unprocessable Entity를 반환해야 한다."""
        response = client.get("/api/endpoint/search")
        assert response.status_code == 422


# ============================================
# 테스트: Audit Log API
# ============================================


class TestAuditAPI:
    def test_audit_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/audit")
        assert response.status_code == 200

    def test_audit_contains_logs(self, client: TestClient) -> None:
        response = client.get("/api/audit")
        data = response.json()
        assert "logs" in data


# ============================================
# 테스트: Capacity Report API
# ============================================


class TestCapacityAPI:
    def test_capacity_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/capacity")
        assert response.status_code == 200

    def test_capacity_contains_nodes(self, client: TestClient) -> None:
        response = client.get("/api/capacity")
        data = response.json()
        assert "nodes" in data


# ============================================
# 테스트: Topology Viewer API
# ============================================


class TestTopologyAPI:
    def test_topology_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/topology")
        assert response.status_code == 200

    def test_topology_contains_spines_and_leaves(self, client: TestClient) -> None:
        response = client.get("/api/topology")
        data = response.json()
        assert "spines" in data
        assert "leaves" in data


# ============================================
# 테스트: All-in-One API
# ============================================


class TestAllAPI:
    def test_all_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/all")
        assert response.status_code == 200

    def test_all_contains_all_modules(self, client: TestClient) -> None:
        """전체 조회 응답에 7개 모듈 키가 모두 포함되어야 한다."""
        response = client.get("/api/all")
        data = response.json()
        expected_keys = {
            "health",
            "policy",
            "interface",
            "endpoint",
            "audit",
            "capacity",
            "topology",
        }
        assert expected_keys.issubset(data.keys())


# ============================================
# TestLinterAPI — GET /api/lint
# ============================================


class TestLinterAPI:
    def test_lint_returns_200(self, client):
        response = client.get("/api/lint")
        assert response.status_code == 200

    def test_lint_response_keys(self, client):
        data = client.get("/api/lint").json()
        assert "source" in data
        assert "total_issues" in data
        assert "summary" in data
        assert "results" in data

    def test_lint_summary_keys(self, client):
        summary = client.get("/api/lint").json()["summary"]
        assert "critical" in summary
        assert "warning" in summary

    def test_lint_source_is_live(self, client):
        data = client.get("/api/lint").json()
        assert data["source"] == "live"

    def test_lint_empty_aci_returns_zero_issues(self, client):
        # ACIClient가 빈 배열을 반환하므로 이슈 0개 예상
        data = client.get("/api/lint").json()
        assert data["total_issues"] == 0
        assert data["results"] == []


# ============================================
# TestLinterUploadAPI — POST /api/lint/upload
# ============================================


class TestLinterUploadAPI:
    """
    파일 업로드 기반 Linter 테스트.
    실제 APIC 없이 규칙별 탐지 동작을 검증.
    """

    def _upload(self, client, payload: dict):
        """JSON payload를 파일로 업로드하는 헬퍼"""
        import json

        content = json.dumps(payload).encode("utf-8")
        return client.post(
            "/api/lint/upload",
            files={"file": ("test.json", content, "application/json")},
        )

    # ------------------------------------------
    # 기본 응답 구조 검증
    # ------------------------------------------

    def test_upload_returns_200(self, client):
        response = self._upload(client, {"imdata": []})
        assert response.status_code == 200

    def test_upload_response_keys(self, client):
        data = self._upload(client, {"imdata": []}).json()
        assert "source" in data
        assert "total_issues" in data
        assert "summary" in data
        assert "results" in data

    def test_upload_source_is_upload(self, client):
        data = self._upload(client, {"imdata": []}).json()
        assert data["source"] == "upload"

    def test_upload_empty_imdata_returns_zero_issues(self, client):
        data = self._upload(client, {"imdata": []}).json()
        assert data["total_issues"] == 0

    # ------------------------------------------
    # 오류 처리 검증
    # ------------------------------------------

    def test_upload_non_json_file_returns_400(self, client):
        response = client.post(
            "/api/lint/upload",
            files={"file": ("test.txt", b"not json", "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_invalid_json_returns_400(self, client):
        response = client.post(
            "/api/lint/upload",
            files={"file": ("test.json", b"{invalid json}", "application/json")},
        )
        assert response.status_code == 400

    # ------------------------------------------
    # SEC-001: permitAll 계열 Contract 탐지
    # ------------------------------------------

    def test_sec_001_detects_risky_contract(self, client):
        payload = {
            "imdata": [
                {
                    "vzBrCP": {
                        "attributes": {
                            "name": "permitAll",
                            "dn": "uni/tn-T1/brc-permitAll",
                        }
                    }
                }
            ]
        }
        data = self._upload(client, payload).json()
        rule_ids = [r["rule_id"] for r in data["results"]]
        assert "SEC-001" in rule_ids

    def test_sec_001_clean_contract_no_issue(self, client):
        payload = {
            "imdata": [
                {
                    "vzBrCP": {
                        "attributes": {
                            "name": "CON-WebToDB",
                            "dn": "uni/tn-T1/brc-CON-WebToDB",
                        }
                    }
                }
            ]
        }
        data = self._upload(client, payload).json()
        rule_ids = [r["rule_id"] for r in data["results"]]
        assert "SEC-001" not in rule_ids

    # ------------------------------------------
    # SEC-002: Subject 없는 빈 Contract 탐지
    # ------------------------------------------

    def test_sec_002_detects_empty_contract(self, client):
        payload = {
            "imdata": [
                {
                    "vzBrCP": {
                        "attributes": {
                            "name": "CON-Empty",
                            "dn": "uni/tn-T1/brc-CON-Empty",
                        }
                    }
                }
                # vzSubj 없음 → SEC-002 발생
            ]
        }
        data = self._upload(client, payload).json()
        rule_ids = [r["rule_id"] for r in data["results"]]
        assert "SEC-002" in rule_ids

    def test_sec_002_contract_with_subject_no_issue(self, client):
        payload = {
            "imdata": [
                {
                    "vzBrCP": {
                        "attributes": {"name": "CON-Web", "dn": "uni/tn-T1/brc-CON-Web"}
                    }
                },
                {
                    "vzSubj": {
                        "attributes": {
                            "name": "Subj1",
                            "dn": "uni/tn-T1/brc-CON-Web/subj-Subj1",
                        }
                    }
                },
            ]
        }
        data = self._upload(client, payload).json()
        rule_ids = [r["rule_id"] for r in data["results"]]
        assert "SEC-002" not in rule_ids

    # ------------------------------------------
    # BP-001: EPG에 BD 미연결 탐지
    # ------------------------------------------

    def test_bp_001_detects_epg_without_bd(self, client):
        payload = {
            "imdata": [
                {
                    "fvAEPg": {
                        "attributes": {
                            "name": "EPG-Web",
                            "dn": "uni/tn-T1/ap-AP1/epg-EPG-Web",
                        }
                    }
                }
                # fvRsBd 없음 → BP-001 발생
            ]
        }
        data = self._upload(client, payload).json()
        rule_ids = [r["rule_id"] for r in data["results"]]
        assert "BP-001" in rule_ids

    def test_bp_001_epg_with_bd_no_issue(self, client):
        payload = {
            "imdata": [
                {
                    "fvAEPg": {
                        "attributes": {
                            "name": "EPG-Web",
                            "dn": "uni/tn-T1/ap-AP1/epg-EPG-Web",
                        }
                    }
                },
                {
                    "fvRsBd": {
                        "attributes": {
                            "dn": "uni/tn-T1/ap-AP1/epg-EPG-Web/rsbd",
                            "tnFvBDName": "BD-Web",
                        }
                    }
                },
            ]
        }
        data = self._upload(client, payload).json()
        rule_ids = [r["rule_id"] for r in data["results"]]
        assert "BP-001" not in rule_ids

    # ------------------------------------------
    # NM-001: 이름에 공백/특수문자 탐지
    # ------------------------------------------

    def test_nm_001_detects_invalid_characters(self, client):
        payload = {
            "imdata": [
                {
                    "fvTenant": {
                        "attributes": {"name": "My Tenant!", "dn": "uni/tn-My Tenant!"}
                    }
                }
            ]
        }
        data = self._upload(client, payload).json()
        rule_ids = [r["rule_id"] for r in data["results"]]
        assert "NM-001" in rule_ids

    def test_nm_001_valid_name_no_issue(self, client):
        payload = {
            "imdata": [
                {
                    "fvTenant": {
                        "attributes": {
                            "name": "TN-Production",
                            "dn": "uni/tn-TN-Production",
                        }
                    }
                }
            ]
        }
        data = self._upload(client, payload).json()
        rule_ids = [r["rule_id"] for r in data["results"]]
        assert "NM-001" not in rule_ids

    # ------------------------------------------
    # severity 및 category 값 검증
    # ------------------------------------------

    def test_result_severity_values_are_valid(self, client):
        payload = {
            "imdata": [
                {
                    "vzBrCP": {
                        "attributes": {
                            "name": "permitAll",
                            "dn": "uni/tn-T1/brc-permitAll",
                        }
                    }
                }
            ]
        }
        data = self._upload(client, payload).json()
        for result in data["results"]:
            assert result["severity"] in ("critical", "warning")

    def test_result_category_values_are_valid(self, client):
        payload = {
            "imdata": [
                {
                    "vzBrCP": {
                        "attributes": {
                            "name": "permitAll",
                            "dn": "uni/tn-T1/brc-permitAll",
                        }
                    }
                }
            ]
        }
        data = self._upload(client, payload).json()
        for result in data["results"]:
            assert result["category"] in ("Security", "BestPractice", "Naming")


# ============================================
# TestSimulatorTenantsAPI — GET /api/simulate/tenants
# ============================================


class TestSimulatorTenantsAPI:
    def test_tenants_returns_200(self, client: TestClient) -> None:
        """Tenant 목록 조회 시 200을 반환해야 한다."""
        response = client.get("/api/simulate/tenants")
        assert response.status_code == 200

    def test_tenants_returns_list(self, client: TestClient) -> None:
        """응답이 리스트 형태여야 한다. ACIClient가 빈 배열을 반환하므로 빈 리스트."""
        response = client.get("/api/simulate/tenants")
        assert isinstance(response.json(), list)


# ============================================
# TestSimulatorEpgsAPI — GET /api/simulate/epgs
# ============================================


class TestSimulatorEpgsAPI:
    def test_epgs_returns_200(self, client: TestClient) -> None:
        """EPG 목록 조회 시 200을 반환해야 한다."""
        response = client.get("/api/simulate/epgs")
        assert response.status_code == 200

    def test_epgs_returns_list(self, client: TestClient) -> None:
        """응답이 리스트 형태여야 한다."""
        response = client.get("/api/simulate/epgs")
        assert isinstance(response.json(), list)

    def test_epgs_with_tenant_filter_returns_200(self, client: TestClient) -> None:
        """tenant 파라미터 지정 시에도 200을 반환해야 한다."""
        response = client.get("/api/simulate/epgs?tenant=TenantA")
        assert response.status_code == 200


# ============================================
# TestSimulatorAPI — POST /api/simulate
# ============================================


class TestSimulatorAPI:
    """
    시뮬레이션 판정 테스트.

    DENY 케이스: ACIClient.get()이 빈 배열을 반환하므로
                 Contract 없음 → ACI Whitelist 모델 기준 Deny-All 적용.
    ALLOW 케이스: SimulatorEngine.simulate()를 직접 패치하여
                  실제 APIC 데이터 없이 ALLOW 시나리오 검증.
    """

    def _simulate(self, client: TestClient, src: str, dst: str):
        """시뮬레이션 요청 헬퍼"""
        return client.post(
            "/api/simulate",
            json={"src_epg_dn": src, "dst_epg_dn": dst},
        )

    # ------------------------------------------
    # 기본 응답 구조 검증
    # ------------------------------------------

    def test_simulate_returns_200(self, client: TestClient) -> None:
        """유효한 요청에 200을 반환해야 한다."""
        response = self._simulate(client, SRC_EPG_DN, DST_EPG_DN)
        assert response.status_code == 200

    def test_simulate_response_keys(self, client: TestClient) -> None:
        """응답에 필수 키가 모두 포함되어야 한다."""
        data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        required = {
            "verdict",
            "src_epg",
            "dst_epg",
            "src_tenant",
            "dst_tenant",
            "matched_contracts",
            "reason",
        }
        assert required.issubset(data.keys())

    def test_simulate_verdict_is_valid_value(self, client: TestClient) -> None:
        """verdict 값은 ALLOW 또는 DENY여야 한다."""
        data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert data["verdict"] in ("ALLOW", "DENY")

    # ------------------------------------------
    # DENY 판정 검증 (빈 ACIClient 응답 기반)
    # ------------------------------------------

    def test_simulate_deny_when_no_contracts(self, client: TestClient) -> None:
        """Contract 없으면 DENY를 반환해야 한다 (ACI Whitelist 모델 기본값)."""
        data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert data["verdict"] == "DENY"

    def test_simulate_deny_has_empty_contracts(self, client: TestClient) -> None:
        """DENY 판정 시 matched_contracts는 빈 리스트여야 한다."""
        data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert data["matched_contracts"] == []

    def test_simulate_deny_has_reason(self, client: TestClient) -> None:
        """DENY 판정 시 reason 필드가 비어있지 않아야 한다."""
        data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert len(data["reason"]) > 0

    # ------------------------------------------
    # ALLOW 판정 검증 (SimulatorEngine.simulate 패치)
    # ------------------------------------------

    def test_simulate_allow_verdict(self, client: TestClient) -> None:
        """Contract가 존재하면 ALLOW를 반환해야 한다."""
        with patch(
            "services.simulator_engine.SimulatorEngine.simulate",
            return_value=MOCK_SIMULATE_ALLOW,
        ):
            data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert data["verdict"] == "ALLOW"

    def test_simulate_allow_contains_contract(self, client: TestClient) -> None:
        """ALLOW 판정 시 matched_contracts에 Contract 정보가 포함되어야 한다."""
        with patch(
            "services.simulator_engine.SimulatorEngine.simulate",
            return_value=MOCK_SIMULATE_ALLOW,
        ):
            data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert len(data["matched_contracts"]) > 0
        assert data["matched_contracts"][0]["name"] == "web-to-db"

    def test_simulate_allow_contract_has_subjects(self, client: TestClient) -> None:
        """ALLOW 판정 Contract에 Subject 및 Filter 정보가 포함되어야 한다."""
        with patch(
            "services.simulator_engine.SimulatorEngine.simulate",
            return_value=MOCK_SIMULATE_ALLOW,
        ):
            data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        contract = data["matched_contracts"][0]
        assert len(contract["subjects"]) > 0
        assert len(contract["subjects"][0]["filters"]) > 0

    # ------------------------------------------
    # 유효성 검증 (400 / 422)
    # ------------------------------------------

    def test_simulate_same_epg_returns_400(self, client: TestClient) -> None:
        """Source와 Destination EPG가 동일하면 400을 반환해야 한다."""
        response = self._simulate(client, SRC_EPG_DN, SRC_EPG_DN)
        assert response.status_code == 400

    def test_simulate_missing_src_returns_422(self, client: TestClient) -> None:
        """src_epg_dn 누락 시 422를 반환해야 한다."""
        response = client.post(
            "/api/simulate",
            json={"dst_epg_dn": DST_EPG_DN},
        )
        assert response.status_code == 422

    def test_simulate_missing_dst_returns_422(self, client: TestClient) -> None:
        """dst_epg_dn 누락 시 422를 반환해야 한다."""
        response = client.post(
            "/api/simulate",
            json={"src_epg_dn": SRC_EPG_DN},
        )
        assert response.status_code == 422


class TestACIClientFailover:
    """
    ACIClient Failover / 에러핸들링 단위 테스트 (v1.5.0)

    - conftest.py가 ACIClient를 모듈 레벨에서 patch하므로,
      패치 전에 저장한 _RealACIClient로 실제 인스턴스를 생성
    - _load_config patch: config.yaml 파일 없이 config dict 직접 주입
    - Session.post patch: login() Failover 시나리오 제어
    - Session.get patch:  get() 세션 만료(401) 시나리오 제어
    """

    # 테스트용 config — hosts 3개 (Primary + Failover 2개)
    MOCK_CONFIG = {
        "apic": {
            "hosts": [
                "https://apic1.test",
                "https://apic2.test",
                "https://apic3.test",
            ],
            "username": "admin",
            "password": "test1234",
            "timeout": 5,
            "retry": 3,
        },
        "linter": {"naming": {"enabled": True}},
    }

    def _make_client(self):
        """
        실제 ACIClient 인스턴스 생성 헬퍼

        conftest.py가 ACIClient를 모듈 레벨에서 patch하므로,
        패치 전에 저장한 _RealACIClient를 사용해 실제 인스턴스를 생성한다.
        _load_config를 patch해서 MOCK_CONFIG를 직접 주입한다.
        """
        import conftest as cf

        with patch.object(
            cf._RealACIClient,
            "_load_config",
            return_value=self.MOCK_CONFIG,
        ):
            return cf._RealACIClient("dummy.yaml")

    def test_failover_on_first_host_down(self):
        """
        Primary APIC 연결 실패 시 Secondary로 자동 전환 검증

        시나리오:
          hosts[0] (apic1) → ConnectionError (Down)
          hosts[1] (apic2) → HTTP 200 (Up)
          기대: self.apic == "https://apic2.test"
        """
        client = self._make_client()

        ok_response = MagicMock()
        ok_response.ok = True

        with patch.object(
            client.session,
            "post",
            side_effect=[
                requests.exceptions.ConnectionError("apic1 down"),
                ok_response,
            ],
        ):
            result = client.login()

        assert result is True
        assert client.apic == "https://apic2.test"
        assert client.logged_in is True

    def test_all_hosts_down_returns_empty(self):
        """
        모든 APIC host 연결 실패 시 get() 빈 배열 반환 검증

        시나리오:
          hosts[0,1,2] 전부 → ConnectionError
          기대: login() == False, get() == []
        """
        client = self._make_client()

        with patch.object(
            client.session,
            "post",
            side_effect=requests.exceptions.ConnectionError("all down"),
        ):
            with patch.object(client.session, "get") as mock_get:
                result = client.get("faultInst")

        assert result == []
        assert client.logged_in is False
        mock_get.assert_not_called()

    def test_session_expired_relogin(self):
        """
        APIC 세션 만료(401) 시 자동 재로그인 후 재시도 검증

        시나리오:
          get() 1회차 → HTTP 401 (세션 만료)
          login() 재시도 → 성공
          get() 2회차 → HTTP 200, imdata 정상 반환
          기대: 결과 == 정상 데이터
        """
        client = self._make_client()
        client.logged_in = True

        expired_response = MagicMock()
        expired_response.status_code = 401
        expired_response.json.return_value = {"imdata": []}

        relogin_response = MagicMock()
        relogin_response.ok = True

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {
            "imdata": [{"faultInst": {"attributes": {"severity": "critical"}}}]
        }

        with patch.object(client.session, "post", return_value=relogin_response):
            with patch.object(
                client.session,
                "get",
                side_effect=[expired_response, ok_response],
            ):
                result = client.get("faultInst")

        assert len(result) == 1
        assert "faultInst" in result[0]
