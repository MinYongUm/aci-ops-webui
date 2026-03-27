# ============================================
# ACI Ops WebUI - API Test Suite
# 버전: v1.9.0
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
from unittest.mock import MagicMock, mock_open, patch
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

    _config_ready 패치:
    - CI 환경(config.yaml 없음)에서 SetupRedirectMiddleware가
      모든 요청을 /setup으로 리다이렉트하는 것을 방지
    - _try_init_aci()는 os.path.exists를 직접 사용하므로
      conftest.py의 ACIClient 패치로 처리됨
    """
    with (
        patch("main.ACIClient") as mock_aci_class,
        patch("main._config_ready", return_value=True),
    ):
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
    def _simulate(self, client: TestClient, src: str, dst: str):
        """시뮬레이션 요청 헬퍼"""
        return client.post(
            "/api/simulate",
            json={"src_epg_dn": src, "dst_epg_dn": dst},
        )

    def test_simulate_returns_200(self, client: TestClient) -> None:
        response = self._simulate(client, SRC_EPG_DN, DST_EPG_DN)
        assert response.status_code == 200

    def test_simulate_response_keys(self, client: TestClient) -> None:
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
        data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert data["verdict"] in ("ALLOW", "DENY")

    def test_simulate_deny_when_no_contracts(self, client: TestClient) -> None:
        data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert data["verdict"] == "DENY"

    def test_simulate_deny_has_empty_contracts(self, client: TestClient) -> None:
        data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert data["matched_contracts"] == []

    def test_simulate_deny_has_reason(self, client: TestClient) -> None:
        data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert len(data["reason"]) > 0

    def test_simulate_allow_verdict(self, client: TestClient) -> None:
        with patch(
            "services.simulator_engine.SimulatorEngine.simulate",
            return_value=MOCK_SIMULATE_ALLOW,
        ):
            data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert data["verdict"] == "ALLOW"

    def test_simulate_allow_contains_contract(self, client: TestClient) -> None:
        with patch(
            "services.simulator_engine.SimulatorEngine.simulate",
            return_value=MOCK_SIMULATE_ALLOW,
        ):
            data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        assert len(data["matched_contracts"]) > 0
        assert data["matched_contracts"][0]["name"] == "web-to-db"

    def test_simulate_allow_contract_has_subjects(self, client: TestClient) -> None:
        with patch(
            "services.simulator_engine.SimulatorEngine.simulate",
            return_value=MOCK_SIMULATE_ALLOW,
        ):
            data = self._simulate(client, SRC_EPG_DN, DST_EPG_DN).json()
        contract = data["matched_contracts"][0]
        assert len(contract["subjects"]) > 0
        assert len(contract["subjects"][0]["filters"]) > 0

    def test_simulate_same_epg_returns_400(self, client: TestClient) -> None:
        response = self._simulate(client, SRC_EPG_DN, SRC_EPG_DN)
        assert response.status_code == 400

    def test_simulate_missing_src_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/simulate",
            json={"dst_epg_dn": DST_EPG_DN},
        )
        assert response.status_code == 422

    def test_simulate_missing_dst_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/simulate",
            json={"src_epg_dn": SRC_EPG_DN},
        )
        assert response.status_code == 422


# ============================================
# TestACIClientFailover
# ============================================


class TestACIClientFailover:
    """ACIClient Failover / 에러핸들링 단위 테스트 (v1.5.0)"""

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
        import conftest as cf

        with patch.object(
            cf._RealACIClient,
            "_load_config",
            return_value=self.MOCK_CONFIG,
        ):
            return cf._RealACIClient("dummy.yaml")

    def test_failover_on_first_host_down(self):
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


# ============================================
# TestSetupTestAPI — POST /api/setup/test
# ============================================


class TestSetupTestAPI:
    """APIC 연결 테스트 API 검증"""

    ENDPOINT = "/api/setup/test"
    VALID_PAYLOAD = {
        "hosts": ["https://192.168.1.1"],
        "username": "admin",
        "password": "testpass",
        "timeout": 30,
        "retry": 3,
    }

    def test_test_connection_success(self, client):
        mock_resp = MagicMock()
        mock_resp.ok = True

        with patch("routers.setup.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            mock_session_cls.return_value = mock_session
            resp = client.post(self.ENDPOINT, json=self.VALID_PAYLOAD)

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["connected_host"] != ""

    def test_test_connection_auth_failure(self, client):
        mock_resp = MagicMock()
        mock_resp.ok = False

        with patch("routers.setup.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            mock_session_cls.return_value = mock_session
            resp = client.post(self.ENDPOINT, json=self.VALID_PAYLOAD)

        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_test_connection_timeout(self, client):
        with patch("routers.setup.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.post.side_effect = requests.exceptions.Timeout()
            mock_session_cls.return_value = mock_session
            resp = client.post(self.ENDPOINT, json=self.VALID_PAYLOAD)

        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_test_connection_unreachable(self, client):
        with patch("routers.setup.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.post.side_effect = requests.exceptions.ConnectionError()
            mock_session_cls.return_value = mock_session
            resp = client.post(self.ENDPOINT, json=self.VALID_PAYLOAD)

        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_test_connection_empty_hosts(self, client):
        payload = {**self.VALID_PAYLOAD, "hosts": []}
        resp = client.post(self.ENDPOINT, json=payload)

        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_test_connection_host_without_scheme(self, client):
        mock_resp = MagicMock()
        mock_resp.ok = True
        payload = {**self.VALID_PAYLOAD, "hosts": ["192.168.1.1"]}

        with patch("routers.setup.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            mock_session_cls.return_value = mock_session
            resp = client.post(self.ENDPOINT, json=payload)

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["connected_host"].startswith("https://")

    def test_test_connection_failover(self, client):
        mock_ok = MagicMock()
        mock_ok.ok = True
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise requests.exceptions.ConnectionError()
            return mock_ok

        payload = {
            **self.VALID_PAYLOAD,
            "hosts": ["https://192.168.1.1", "https://192.168.1.2"],
        }

        with patch("routers.setup.requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.post.side_effect = side_effect
            mock_session_cls.return_value = mock_session
            resp = client.post(self.ENDPOINT, json=payload)

        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ============================================
# TestSetupSaveAPI — POST /api/setup/save
# ============================================


class TestSetupSaveAPI:
    """설정 저장 API 검증"""

    ENDPOINT = "/api/setup/save"
    VALID_PAYLOAD = {
        "hosts": ["https://192.168.1.1"],
        "username": "admin",
        "password": "testpass",
        "timeout": 30,
        "retry": 3,
    }

    def test_save_success(self, client):
        mock_resp = MagicMock()
        mock_resp.ok = True

        with (
            patch("routers.setup.requests.Session") as mock_session_cls,
            patch("builtins.open", mock_open()),
            patch("routers.setup.yaml.dump") as mock_dump,
        ):
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            mock_session_cls.return_value = mock_session
            resp = client.post(self.ENDPOINT, json=self.VALID_PAYLOAD)

        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_dump.assert_called_once()

    def test_save_blocked_on_connection_failure(self, client):
        mock_resp = MagicMock()
        mock_resp.ok = False

        with (
            patch("routers.setup.requests.Session") as mock_session_cls,
            patch("builtins.open", mock_open()) as mock_file,
        ):
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            mock_session_cls.return_value = mock_session
            resp = client.post(self.ENDPOINT, json=self.VALID_PAYLOAD)

        assert resp.status_code == 200
        assert resp.json()["success"] is False
        for call in mock_file.call_args_list:
            assert "w" not in call.args and call.kwargs.get("mode") != "w"

    def test_save_config_structure(self, client):
        mock_resp = MagicMock()
        mock_resp.ok = True
        captured = {}

        def capture_dump(data, *args, **kwargs):
            captured["data"] = data

        with (
            patch("routers.setup.requests.Session") as mock_session_cls,
            patch("builtins.open", mock_open()),
            patch("routers.setup.yaml.dump", side_effect=capture_dump),
        ):
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            mock_session_cls.return_value = mock_session
            client.post(self.ENDPOINT, json=self.VALID_PAYLOAD)

        cfg = captured.get("data", {})
        assert "apic" in cfg
        assert "hosts" in cfg["apic"]
        assert isinstance(cfg["apic"]["hosts"], list)
        assert cfg["apic"]["username"] == "admin"
        assert "linter" in cfg

    def test_save_file_write_error(self, client):
        mock_resp = MagicMock()
        mock_resp.ok = True

        with (
            patch("routers.setup.requests.Session") as mock_session_cls,
            patch("builtins.open", side_effect=OSError("Permission denied")),
        ):
            mock_session = MagicMock()
            mock_session.post.return_value = mock_resp
            mock_session_cls.return_value = mock_session
            resp = client.post(self.ENDPOINT, json=self.VALID_PAYLOAD)

        assert resp.status_code == 200
        assert resp.json()["success"] is False
        assert "저장 실패" in resp.json()["message"]


# ============================================
# TestSetupMiddleware — Middleware 동작 검증
# ============================================


class TestSetupMiddleware:
    """SetupRedirectMiddleware 동작 테스트"""

    def test_redirect_when_no_config(self, client):
        """config.yaml 없으면 / 접속 시 /setup으로 리다이렉트"""
        with patch("main._config_ready", return_value=False):
            resp = client.get("/", follow_redirects=False)

        assert resp.status_code in (302, 307)
        assert "/setup" in resp.headers.get("location", "")

    def test_setup_page_always_accessible(self, client):
        """config.yaml 없어도 /setup은 Middleware를 통과해야 한다"""
        from starlette.responses import Response

        with (
            patch("main._config_ready", return_value=False),
            patch(
                "main.FileResponse",
                return_value=Response(content="ok", status_code=200),
            ),
        ):
            resp = client.get("/setup", follow_redirects=False)

        assert resp.status_code not in (302, 307)
