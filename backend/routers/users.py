# ============================================
# Users Router
# 목적: 사용자 계정 관리 (admin 전용)
# ============================================

import logging
from typing import List

from fastapi import APIRouter, Cookie, Depends, HTTPException
from pydantic import BaseModel, field_validator

from services.auth_service import (
    ROLE_ADMIN,
    VALID_ROLES,
    change_password,
    create_user,
    decode_access_token,
    delete_user,
    list_users,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


# ============================================
# 요청/응답 모델
# ============================================


class UserResponse(BaseModel):
    username: str
    role: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(VALID_ROLES)}")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Username cannot be empty.")
        if len(v) > 32:
            raise ValueError("Username must be 32 characters or less.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


class ChangePasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


# ============================================
# admin 권한 확인 Dependency
# ============================================


def require_admin(access_token: str = Cookie(default=None)) -> dict:
    """
    admin 역할 확인 Dependency.
    - 쿠키 없거나 admin이 아니면 403 반환
    """
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    user = decode_access_token(access_token)
    if not user:
        raise HTTPException(status_code=401, detail="Token expired or invalid.")

    if user.get("role") != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required.")

    return user


# ============================================
# 엔드포인트
# ============================================


@router.get("", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_admin)) -> List[UserResponse]:
    """
    전체 사용자 목록 조회 (비밀번호 제외).
    admin 전용.
    """
    return list_users()


@router.post("", response_model=dict)
async def create_user_endpoint(
    req: CreateUserRequest,
    current_user: dict = Depends(require_admin),
) -> dict:
    """
    사용자 생성.
    admin 전용. 중복 username이면 409 반환.
    """
    try:
        created = create_user(req.username, req.password, req.role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not created:
        raise HTTPException(
            status_code=409, detail=f"User '{req.username}' already exists."
        )

    return {"success": True, "message": f"User '{req.username}' created."}


@router.delete("/{username}", response_model=dict)
async def delete_user_endpoint(
    username: str,
    current_user: dict = Depends(require_admin),
) -> dict:
    """
    사용자 삭제.
    admin 전용. 자기 자신 또는 마지막 admin 삭제 시 400 반환.
    """
    try:
        deleted = delete_user(username, requester=current_user["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not deleted:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

    return {"success": True, "message": f"User '{username}' deleted."}


@router.put("/{username}/password", response_model=dict)
async def change_password_endpoint(
    username: str,
    req: ChangePasswordRequest,
    current_user: dict = Depends(require_admin),
) -> dict:
    """
    비밀번호 변경.
    admin은 모든 사용자 비밀번호 변경 가능.
    """
    changed = change_password(username, req.new_password)
    if not changed:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

    return {"success": True, "message": f"Password changed for '{username}'."}
