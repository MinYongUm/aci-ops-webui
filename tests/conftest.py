# ============================================
# ACI Ops WebUI - pytest 공통 픽스처
# 버전: v1.9.2
# 목적: main.py import 시 발생하는 모듈 레벨 실행을
#       실제 파일/디렉토리 없이 통과시키기 위한 사전 패치
#
# 패치 대상:
#   1. ACIClient()           → config.yaml 없어도 통과
#   2. StaticFiles(...)      → ../frontend 디렉토리 없어도 통과
#   3. init_default_admin()  → users.yaml 자동 생성 방지 (v1.9.2)
#   4. decode_access_token() → AuthMiddleware 우회 (v1.9.2)
#
# [v1.9.2 설계 노트]
# _get_secret_key()는 auth_service 임포트 시점에 SECRET_KEY 상수로
# 즉시 실행되므로 모듈 레벨 패치 불가. backend/.secret_key 파일은
# 테스트 실행 시 자동 생성되며 .gitignore 처리됨.
# ============================================

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# backend/ 경로를 sys.path에 추가 (conftest에서 한 번만 처리)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# ============================================
# 패치 전에 원본 ACIClient 클래스 저장 (v1.5.0)
# TestACIClientFailover에서 실제 인스턴스 생성 시 사용
# ============================================
import services.aci_client as _aci_module

_RealACIClient = _aci_module.ACIClient

# ============================================
# 모듈 레벨 패치 (모든 테스트에 공통 적용)
# ============================================

# ACIClient 패치 — config.yaml 읽기 방지
_patcher_aci = patch("services.aci_client.ACIClient")
mock_aci_class = _patcher_aci.start()
mock_aci_class.return_value = MagicMock()

# StaticFiles 패치 — ../frontend 경로 없어도 통과
_patcher_static = patch("fastapi.staticfiles.StaticFiles.__init__", return_value=None)
_patcher_static.start()

# ============================================
# 테스트용 Mock 사용자 데이터
# ============================================
MOCK_ADMIN_USER = {"username": "admin", "role": "admin"}


# ============================================
# client fixture
# AuthMiddleware + SetupRedirectMiddleware 양쪽 우회
# ============================================
@pytest.fixture()
def client() -> TestClient:
    with (
        patch("main.ACIClient") as mock_aci_class,
        patch("main._config_ready", return_value=True),
        patch("main.init_default_admin"),
        patch("main.decode_access_token", return_value=MOCK_ADMIN_USER),
    ):
        mock_aci = MagicMock()
        mock_aci_class.return_value = mock_aci

        # 패치 적용 후 app import (이미 import된 경우 재사용)
        from main import app

        yield TestClient(
            app, raise_server_exceptions=True, cookies={"access_token": "test-token"}
        )
