# ============================================
# Authentication Service
# 목적: JWT 생성/검증, 비밀번호 해싱, 사용자 관리
# ============================================

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import yaml
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# ============================================
# 상수 정의
# ============================================
USERS_PATH = os.path.join(os.path.dirname(__file__), "..", "users.yaml")
SECRET_KEY_PATH = os.path.join(os.path.dirname(__file__), "..", ".secret_key")

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 8  # APIC 세션 만료 주기와 동일

# bcrypt 컨텍스트 (deprecated 경고 억제)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================
# 역할 상수
# ============================================
ROLE_ADMIN = "admin"
ROLE_VIEWER = "viewer"
VALID_ROLES = {ROLE_ADMIN, ROLE_VIEWER}


# ============================================
# Secret Key 관리
# ============================================


def _get_secret_key() -> str:
    """
    JWT 서명용 Secret Key 반환.
    파일에 저장된 키를 사용하며, 없으면 새로 생성.
    """
    if os.path.exists(SECRET_KEY_PATH):
        with open(SECRET_KEY_PATH, "r") as f:
            return f.read().strip()

    # 최초 실행 시 랜덤 키 생성
    import secrets

    key = secrets.token_hex(32)
    with open(SECRET_KEY_PATH, "w") as f:
        f.write(key)
    logger.info("JWT secret key generated.")
    return key


SECRET_KEY = _get_secret_key()


# ============================================
# users.yaml CRUD
# ============================================


def _load_users() -> dict:
    """
    users.yaml 로드.
    파일 없거나 비어있으면 빈 딕셔너리 반환.
    """
    if not os.path.exists(USERS_PATH):
        return {}
    try:
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data.get("users", {})
    except Exception as e:
        logger.error(f"Failed to load users.yaml: {e}")
        return {}


def _save_users(users: dict) -> None:
    """
    users.yaml 저장.

    Args:
        users: {username: {hashed_password, role}} 딕셔너리
    """
    try:
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            yaml.dump({"users": users}, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        logger.error(f"Failed to save users.yaml: {e}")
        raise


def users_initialized() -> bool:
    """users.yaml에 사용자가 1명 이상 존재하는지 확인."""
    return bool(_load_users())


# ============================================
# 비밀번호 해싱
# ============================================


def hash_password(plain: str) -> str:
    """평문 비밀번호를 bcrypt 해시로 변환."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """평문 비밀번호와 해시 비교."""
    return pwd_context.verify(plain, hashed)


# ============================================
# 사용자 인증
# ============================================


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    사용자 인증.

    Args:
        username: 사용자명
        password: 평문 비밀번호
    Returns:
        인증 성공 시 {username, role} 딕셔너리, 실패 시 None
    """
    users = _load_users()
    user = users.get(username)
    if not user:
        return None
    if not verify_password(password, user.get("hashed_password", "")):
        return None
    return {"username": username, "role": user.get("role", ROLE_VIEWER)}


# ============================================
# JWT 생성 / 검증
# ============================================


def create_access_token(username: str, role: str) -> str:
    """
    JWT Access Token 생성.

    Args:
        username: 사용자명
        role: 역할 (admin / viewer)
    Returns:
        JWT 토큰 문자열
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    JWT 토큰 디코딩.

    Args:
        token: JWT 토큰 문자열
    Returns:
        {username, role} 딕셔너리, 유효하지 않으면 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if not username or not role:
            return None
        return {"username": username, "role": role}
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token expired.")
        return None
    except jwt.PyJWTError as e:
        logger.debug(f"JWT decode error: {e}")
        return None


# ============================================
# 사용자 관리 (admin 전용)
# ============================================


def list_users() -> list:
    """
    전체 사용자 목록 반환 (비밀번호 제외).

    Returns:
        [{username, role}, ...] 리스트
    """
    users = _load_users()
    return [
        {"username": uname, "role": info.get("role", ROLE_VIEWER)}
        for uname, info in users.items()
    ]


def create_user(username: str, password: str, role: str) -> bool:
    """
    사용자 생성.

    Args:
        username: 사용자명 (중복 불가)
        password: 평문 비밀번호
        role: 역할 (admin / viewer)
    Returns:
        성공 여부
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")

    users = _load_users()
    if username in users:
        return False  # 중복

    users[username] = {
        "hashed_password": hash_password(password),
        "role": role,
    }
    _save_users(users)
    logger.info(f"User created: {username} ({role})")
    return True


def delete_user(username: str, requester: str) -> bool:
    """
    사용자 삭제.

    Args:
        username: 삭제할 사용자명
        requester: 요청자 (자기 자신 삭제 방지)
    Returns:
        성공 여부
    """
    if username == requester:
        raise ValueError("Cannot delete your own account.")

    users = _load_users()
    if username not in users:
        return False

    # admin 계정이 1명뿐인 경우 삭제 방지
    admin_count = sum(1 for u in users.values() if u.get("role") == ROLE_ADMIN)
    if users[username].get("role") == ROLE_ADMIN and admin_count <= 1:
        raise ValueError("Cannot delete the last admin account.")

    del users[username]
    _save_users(users)
    logger.info(f"User deleted: {username} (by {requester})")
    return True


def change_password(username: str, new_password: str) -> bool:
    """
    비밀번호 변경.

    Args:
        username: 대상 사용자명
        new_password: 새 평문 비밀번호
    Returns:
        성공 여부
    """
    users = _load_users()
    if username not in users:
        return False

    users[username]["hashed_password"] = hash_password(new_password)
    _save_users(users)
    logger.info(f"Password changed: {username}")
    return True


def init_default_admin(
    username: str = "admin", password: str = "aci-ops-admin"
) -> bool:
    """
    기본 admin 계정 생성 (users.yaml 없을 때 최초 1회).

    Returns:
        생성 여부 (이미 있으면 False)
    """
    if users_initialized():
        return False
    return create_user(username, password, ROLE_ADMIN)
