# ============================================
# ACI Ops WebUI - Backend Main
# 목적: FastAPI 애플리케이션 진입점
# 버전: v1.9.0 - 초기 설정 UI (config.yaml 미존재 시 /setup 리다이렉트)
#
# 실행 방법:
#   cd backend
#   uvicorn main:app --reload --host 0.0.0.0 --port 8000
# ============================================

import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import FastAPI, Query, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# ============================================
# 경로 설정
# ============================================
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ============================================
# 모듈 import
# ============================================
from routers.audit import get_audit_data
from routers.capacity import get_capacity_data
from routers.endpoint import get_endpoint_data, search_endpoint
from routers.health import get_health_data
from routers.interface import get_interface_data
from routers.linter import get_lint_data, lint_upload
from routers.policy import get_policy_data
from routers.setup import router as setup_router
from routers.simulator import get_simulate_router
from routers.topology import get_topology_data
from services.aci_client import ACIClient

# ============================================
# 로거 설정
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================
# config.yaml 경로
# ============================================
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

# ============================================
# FastAPI 앱 인스턴스 생성
# ============================================
app = FastAPI(
    title="ACI Ops WebUI",
    version="1.9.0",
)

# ============================================
# ACI 클라이언트 초기화 (지연 처리)
# - config.yaml 없으면 None으로 유지 (서버 종료 없음)
# - /setup 저장 완료 후 reinitialize_aci() 호출로 재초기화
# ============================================
aci: ACIClient | None = None


def _config_ready() -> bool:
    """
    config.yaml이 존재하고 내용이 있는지 확인

    - 파일 없음: False
    - 빈 파일 (install.sh가 Docker 마운트용으로 미리 생성): False
    - 내용 있음: True

    Middleware에서 사용 — 테스트 픽스처에서 patch 가능
    """
    return os.path.exists(CONFIG_PATH) and os.path.getsize(CONFIG_PATH) > 0


def _try_init_aci() -> ACIClient | None:
    """
    ACIClient 초기화 시도

    - config.yaml 없으면 None 반환 (서버 종료 없음)
    - 성공 시 ACIClient 인스턴스 반환
    """
    if not os.path.exists(CONFIG_PATH):
        logger.warning("config.yaml 없음 — /setup으로 안내합니다.")
        return None
    try:
        client = ACIClient(config_path=CONFIG_PATH)
        logger.info("ACIClient 초기화 완료")
        return client
    except Exception as e:
        logger.error("ACIClient 초기화 실패: %s", e)
        return None


aci = _try_init_aci()


def reinitialize_aci() -> None:
    """
    /setup 저장 완료 후 ACIClient 재초기화

    routers/setup.py의 setup_save()에서 config.yaml 저장 후 호출
    """
    global aci
    aci = _try_init_aci()


# setup.py에 reinitialize 콜백 주입
import routers.setup as _setup_module  # noqa: E402

_setup_module.reinitialize_aci = reinitialize_aci


# ============================================
# Middleware: config.yaml 미존재/비어있을 때 /setup 리다이렉트
# ============================================
class SetupRedirectMiddleware(BaseHTTPMiddleware):
    """
    config.yaml 없거나 비어있을 때 /setup 이외 요청을 /setup으로 리다이렉트

    통과 허용 경로:
    - /setup          (설정 페이지 HTML)
    - /api/setup/*    (설정 API)
    - /static/*       (정적 파일)
    - /docs, /openapi (FastAPI 자동 문서)
    """

    ALLOWED_PREFIXES = ("/setup", "/api/setup", "/static", "/docs", "/openapi")

    async def dispatch(self, request: Request, call_next):
        # config.yaml 존재하고 내용 있으면 정상 통과
        # 빈 파일(install.sh가 Docker 마운트용으로 생성)은 미설정으로 처리
        if _config_ready():
            return await call_next(request)

        # 허용 경로는 통과
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.ALLOWED_PREFIXES):
            return await call_next(request)

        # 그 외 모든 요청 → /setup 리다이렉트
        logger.info("config.yaml 미설정 — %s → /setup 리다이렉트", path)
        return RedirectResponse(url="/setup")


app.add_middleware(SetupRedirectMiddleware)

# ============================================
# Static 파일 서빙 설정
# ============================================
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# ============================================
# 라우터 등록
# ============================================
app.include_router(setup_router)
app.include_router(get_simulate_router(aci))


# ============================================
# API 엔드포인트 정의
# ============================================


@app.get("/")
async def root():
    """메인 페이지"""
    return FileResponse("../frontend/index.html")


@app.get("/setup")
async def setup_page():
    """초기 설정 페이지"""
    return FileResponse("../frontend/setup.html")


@app.get("/api/health")
async def api_health():
    """Health Check API"""
    return get_health_data(aci)


@app.get("/api/policy")
async def api_policy():
    """Policy Check API"""
    return get_policy_data(aci)


@app.get("/api/interface")
async def api_interface():
    """Interface Monitor API"""
    return get_interface_data(aci)


@app.get("/api/endpoint")
async def api_endpoint():
    """Endpoint Tracker API"""
    return get_endpoint_data(aci)


@app.get("/api/endpoint/search")
async def api_endpoint_search(q: str = Query(..., description="MAC or IP address")):
    """
    Endpoint 검색 API

    - MAC 주소 또는 IP 주소로 검색
    - 위치 정보 (Node, Interface) 포함

    Args:
        q: 검색어 (MAC 또는 IP)
    Returns:
        list: 검색 결과
    """
    return search_endpoint(aci, q)


@app.get("/api/audit")
async def api_audit():
    """Audit Log API"""
    return get_audit_data(aci)


@app.get("/api/capacity")
async def api_capacity():
    """Capacity Report API"""
    return get_capacity_data(aci)


@app.get("/api/topology")
async def api_topology():
    """Topology Viewer API"""
    return get_topology_data(aci)


@app.get("/api/lint")
async def api_lint():
    """Config Linter API — APIC Live 조회"""
    return get_lint_data(aci)


@app.post("/api/lint/upload")
async def api_lint_upload(file: UploadFile):
    """Config Linter API — JSON 파일 업로드"""
    return await lint_upload(file)


@app.get("/api/all")
async def api_all():
    """
    전체 리포트 API (v1.5.0 — 병렬 처리)

    - 7개 모듈을 ThreadPoolExecutor로 동시 조회
    - 가장 느린 모듈 1개의 응답 시간이 전체 응답 시간
    - 모듈 단위 예외 발생 시 해당 모듈만 None 반환 (전체 실패 방지)
    - 대시보드 초기 로딩 시 사용
    """
    tasks = {
        "health": get_health_data,
        "policy": get_policy_data,
        "interface": get_interface_data,
        "endpoint": get_endpoint_data,
        "audit": get_audit_data,
        "capacity": get_capacity_data,
        "topology": get_topology_data,
    }

    results: dict = {}

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_to_key = {executor.submit(fn, aci): key for key, fn in tasks.items()}

        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                logger.error("/api/all 모듈 실행 오류 [%s]: %s", key, exc)
                results[key] = None

    return results
