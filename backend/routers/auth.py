# ============================================
# Auth Router
# 목적: 로그인 / 로그아웃 / 현재 사용자 조회
# ============================================

import logging

from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel

from services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_access_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================
# 요청/응답 모델
# ============================================


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    username: str = ""
    role: str = ""


class MeResponse(BaseModel):
    username: str
    role: str


# ============================================
# 엔드포인트
# ============================================


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, response: Response) -> LoginResponse:
    """
    로그인 API.

    - 인증 성공 시 JWT를 httponly 쿠키로 발급
    - 실패 시 401 반환 (타이밍 공격 방지를 위해 고정 메시지)
    """
    user = authenticate_user(req.username, req.password)
    if not user:
        logger.warning(f"Login failed: {req.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_access_token(user["username"], user["role"])

    # httponly 쿠키: JavaScript에서 접근 불가 (XSS 방어)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=8 * 3600,  # 8시간 (JWT_EXPIRE_HOURS 동기화)
    )

    logger.info(f"Login success: {user['username']} ({user['role']})")
    return LoginResponse(
        success=True,
        message="Login successful.",
        username=user["username"],
        role=user["role"],
    )


@router.post("/logout")
async def logout(response: Response) -> dict:
    """
    로그아웃 API.
    - 쿠키 삭제 (max_age=0)
    """
    response.delete_cookie(key="access_token")
    return {"success": True, "message": "Logged out."}


@router.get("/me", response_model=MeResponse)
async def me(access_token: str = Cookie(default=None)) -> MeResponse:
    """
    현재 로그인 사용자 조회.
    - 쿠키 없거나 만료 시 401 반환
    """
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    user = decode_access_token(access_token)
    if not user:
        raise HTTPException(status_code=401, detail="Token expired or invalid.")

    return MeResponse(username=user["username"], role=user["role"])
