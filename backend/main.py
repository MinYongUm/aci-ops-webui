# ============================================
# ACI Ops WebUI - Backend Main
# 목적: FastAPI 애플리케이션 진입점
# 버전: v1.9.5 - UX 개선 (접속 흐름 변경 + login.html 안내 문구)
#
# 실행 방법:
#   cd backend
#   uvicorn main:app --reload --host 0.0.0.0 --port 8000
# ============================================

import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import FastAPI, UploadFile
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
from routers.auth import router as auth_router
from routers.capacity import get_capacity_data
from routers.endpoint import get_endpoint_data, search_endpoint
from routers.health import get_health_data
from routers.interface import get_interface_data
from routers.linter import get_lint_data, lint_upload
from routers.policy import get_policy_data
from routers.setup import router as setup_router
from routers.simulator import get_simulate_router
from routers.topology import get_topology_data
from routers.users import router as users_router
from services.aci_client import ACIClient
from services.auth_service import decode_access_token, init_default_admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# 상수
# ============================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

# 인증 없이 접근 허용 경로
# v1.9.5: /setup, /api/setup 제거 → 인증 후에만 접근 가능 (보안 강화)
_AUTH_EXEMPT_PREFIXES = (
    "/login",
    "/api/auth",
    "/static",
    "/docs",
    "/openapi",
)

# setup 리다이렉트 허용 경로 (config 미설정 시에도 통과)
_SETUP_ALLOWED_PREFIXES = (
    "/setup",
    "/api/setup",
    "/api/auth",
    "/login",
    "/static",
    "/docs",
    "/openapi",
)


# ============================================
# config.yaml 상태 확인
# ============================================


def _config_ready() -> bool:
    """config.yaml 존재 + 크기 > 0 확인."""
    return os.path.exists(CONFIG_PATH) and os.path.getsize(CONFIG_PATH) > 0


def _try_init_aci() -> "ACIClient | None":
    """config.yaml이 있으면 ACIClient 초기화."""
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        return ACIClient(config_path=CONFIG_PATH)
    except Exception as e:
        logger.warning(f"ACIClient init failed: {e}")
        return None


# ============================================
# ACIClient 초기화 (지연)
# ============================================
aci = _try_init_aci()


def reinitialize_aci() -> None:
    """setup/save 후 ACIClient 재초기화 콜백."""
    global aci
    aci = _try_init_aci()
    logger.info("ACIClient reinitialized.")


# ============================================
# FastAPI 앱 인스턴스 생성
# ============================================
app = FastAPI(title="ACI Ops WebUI", version="1.9.5")


# ============================================
# Middleware 1: Auth 검증
# (로그인 안 된 경우 /login으로 강제)
# ============================================
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 인증 면제 경로는 통과
        if any(path.startswith(p) for p in _AUTH_EXEMPT_PREFIXES):
            return await call_next(request)

        # 쿠키에서 JWT 확인
        token = request.cookies.get("access_token")
        if not token or not decode_access_token(token):
            # API 요청이면 401, 페이지 요청이면 /login 리다이렉트
            if path.startswith("/api/"):
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=401, content={"detail": "Not authenticated."}
                )
            return RedirectResponse(url="/login")

        return await call_next(request)


# ============================================
# Middleware 2: Setup 리다이렉트
# (config.yaml 미설정 시 /setup으로 강제)
# ============================================
class SetupRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not _config_ready():
            if not any(path.startswith(p) for p in _SETUP_ALLOWED_PREFIXES):
                return RedirectResponse(url="/setup")
        return await call_next(request)


# 미들웨어 등록 순서 중요 (Starlette LIFO: 나중 등록 = 먼저 실행):
# v1.9.5: Auth 먼저 실행 → 인증 통과 후 Setup 체크
# 실행 순서: AuthMiddleware → SetupRedirectMiddleware
app.add_middleware(SetupRedirectMiddleware)
app.add_middleware(AuthMiddleware)


# ============================================
# 초기화
# ============================================
import routers.setup as _setup_module  # noqa: E402

_setup_module.reinitialize_aci = reinitialize_aci
init_default_admin()  # users.yaml 없을 때만 기본 admin 생성

# ============================================
# 라우터 등록
# ============================================
app.include_router(setup_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(get_simulate_router(aci))

# ============================================
# Static 파일 서빙
# ============================================
app.mount("/static", StaticFiles(directory="../frontend"), name="static")


# ============================================
# 페이지 라우트
# ============================================


@app.get("/")
async def root():
    """메인 대시보드 페이지."""
    return FileResponse("../frontend/index.html")


@app.get("/login")
async def login_page():
    """로그인 페이지."""
    return FileResponse("../frontend/login.html")


@app.get("/setup")
async def setup_page():
    """초기 설정 페이지."""
    return FileResponse("../frontend/setup.html")


# ============================================
# 데이터 API 엔드포인트
# ============================================


@app.get("/api/health")
async def api_health():
    return get_health_data(aci)


@app.get("/api/policy")
async def api_policy():
    return get_policy_data(aci)


@app.get("/api/interface")
async def api_interface():
    return get_interface_data(aci)


@app.get("/api/endpoint")
async def api_endpoint():
    return get_endpoint_data(aci)


@app.get("/api/endpoint/search")
async def api_endpoint_search(q: str):
    return search_endpoint(aci, q)


@app.get("/api/audit")
async def api_audit():
    return get_audit_data(aci)


@app.get("/api/capacity")
async def api_capacity():
    return get_capacity_data(aci)


@app.get("/api/topology")
async def api_topology():
    return get_topology_data(aci)


@app.get("/api/lint")
async def api_lint():
    return get_lint_data(aci)


@app.post("/api/lint/upload")
async def api_lint_upload(file: UploadFile):
    return await lint_upload(file)


@app.get("/api/all")
async def api_all():
    """전체 데이터 병렬 조회."""
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
