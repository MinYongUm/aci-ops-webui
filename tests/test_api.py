# ============================================
# ACI Ops WebUI - API Test Suite
# 버전: v1.2.0
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

import pytest
from fastapi.testclient import TestClient

# backend/ 디렉토리를 기준으로 import
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app  # noqa: E402


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
    @pytest.mark.skip(reason="GET /는 FileResponse(HTML)를 반환하므로 API 테스트 범위 제외")
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