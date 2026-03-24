# ============================================
# ACI Ops WebUI - pytest 공통 픽스처
# 버전: v1.2.0
# 목적: main.py import 시 발생하는 두 가지 모듈 레벨 실행을
#       실제 파일/디렉토리 없이 통과시키기 위한 사전 패치
#
# 패치 대상:
#   1. ACIClient()        → config.yaml 없어도 통과
#   2. StaticFiles(...)   → ../frontend 디렉토리 없어도 통과
# ============================================

import os
import sys
from unittest.mock import MagicMock, patch

# backend/ 경로를 sys.path에 추가 (conftest에서 한 번만 처리)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# ACIClient 패치 — config.yaml 읽기 방지
_patcher_aci = patch("services.aci_client.ACIClient")
mock_aci_class = _patcher_aci.start()
mock_aci_class.return_value = MagicMock()

# StaticFiles 패치 — ../frontend 경로 없어도 통과
_patcher_static = patch("fastapi.staticfiles.StaticFiles.__init__", return_value=None)
_patcher_static.start()