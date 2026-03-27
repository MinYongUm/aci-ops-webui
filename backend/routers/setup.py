# ============================================
# Setup Router
# 목적: 초기 설정 API (APIC 연결 테스트 및 config.yaml 저장)
# 버전: v1.9.0
# ============================================

import logging
import os
from typing import List

import requests
import yaml
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# config.yaml 경로 (backend/ 디렉토리 기준)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

# ACIClient 재초기화 콜백 (main.py에서 주입)
# config.yaml 저장 완료 후 aci 인스턴스를 갱신하기 위해 사용
reinitialize_aci = None


# ============================================
# Request / Response 스키마
# ============================================


class SetupRequest(BaseModel):
    """초기 설정 요청 스키마"""

    hosts: List[str]  # APIC 주소 목록 (1개 이상)
    username: str  # APIC 계정명
    password: str  # APIC 비밀번호
    timeout: int = 30  # 요청 타임아웃 (초)
    retry: int = 3  # 재시도 횟수


class SetupResponse(BaseModel):
    """초기 설정 응답 스키마"""

    success: bool
    message: str
    connected_host: str = ""  # 실제 연결된 APIC 주소


# ============================================
# 내부 유틸리티
# ============================================


def _test_connection(host: str, username: str, password: str, timeout: int) -> bool:
    """
    단일 APIC 호스트에 대한 연결 테스트

    - aaaLogin.json 엔드포인트로 인증 시도
    - SSL 인증서 검증 비활성화 (Self-signed 대응)

    Args:
        host: APIC 주소 (https:// 포함)
        username: 계정명
        password: 비밀번호
        timeout: 요청 타임아웃 (초)
    Returns:
        bool: 연결 성공 여부
    """
    # https:// 미포함 시 자동 추가
    if not host.startswith("http"):
        host = f"https://{host}"

    auth_payload = {
        "aaaUser": {
            "attributes": {
                "name": username,
                "pwd": password,
            }
        }
    }

    session = requests.Session()
    resp = session.post(
        f"{host}/api/aaaLogin.json",
        json=auth_payload,
        verify=False,
        timeout=timeout,
    )
    return resp.ok


def _normalize_host(host: str) -> str:
    """
    APIC 주소 정규화

    - 앞뒤 공백 제거
    - https:// 미포함 시 추가

    Args:
        host: 입력된 APIC 주소
    Returns:
        str: 정규화된 주소
    """
    host = host.strip()
    if not host.startswith("http"):
        host = f"https://{host}"
    return host


# ============================================
# API 엔드포인트
# ============================================


@router.post("/api/setup/test", response_model=SetupResponse)
async def setup_test(req: SetupRequest) -> SetupResponse:
    """
    APIC 연결 테스트 API

    - hosts 리스트 순서대로 연결 시도
    - 첫 번째 성공한 호스트 반환
    - config.yaml 저장 안 함

    Args:
        req: SetupRequest (hosts, username, password, timeout)
    Returns:
        SetupResponse: 연결 성공 여부 + 연결된 호스트
    """
    if not req.hosts:
        return SetupResponse(success=False, message="APIC 주소를 1개 이상 입력하세요.")

    for raw_host in req.hosts:
        host = _normalize_host(raw_host)
        if not host:
            continue

        try:
            logger.info("APIC 연결 테스트 시도: %s", host)
            ok = _test_connection(host, req.username, req.password, req.timeout)

            if ok:
                logger.info("APIC 연결 성공: %s", host)
                return SetupResponse(
                    success=True,
                    message=f"연결 성공: {host}",
                    connected_host=host,
                )
            else:
                logger.warning("APIC 인증 실패: %s", host)

        except requests.exceptions.ConnectionError:
            logger.warning("APIC 연결 불가: %s", host)
        except requests.exceptions.Timeout:
            logger.warning("APIC 응답 타임아웃: %s", host)
        except Exception as e:
            logger.error("APIC 연결 중 예외 발생: %s — %s", host, e)

    return SetupResponse(
        success=False,
        message="모든 APIC 주소에 연결할 수 없습니다. 주소, 계정, 비밀번호를 확인하세요.",
    )


@router.post("/api/setup/save", response_model=SetupResponse)
async def setup_save(req: SetupRequest) -> SetupResponse:
    """
    APIC 설정 저장 API

    - 연결 테스트 후 성공 시에만 config.yaml 저장
    - 저장 완료 후 프론트엔드가 /로 리다이렉트 처리

    Args:
        req: SetupRequest (hosts, username, password, timeout, retry)
    Returns:
        SetupResponse: 저장 성공 여부
    """
    # 1. 저장 전 연결 테스트 필수
    test_result = await setup_test(req)
    if not test_result.success:
        return SetupResponse(
            success=False,
            message=f"연결 테스트 실패 — 저장 취소. ({test_result.message})",
        )

    # 2. config.yaml 구조 생성
    normalized_hosts = [_normalize_host(h) for h in req.hosts if h.strip()]
    config_data = {
        "apic": {
            "hosts": normalized_hosts,
            "username": req.username,
            "password": req.password,
            "timeout": req.timeout,
            "retry": req.retry,
        },
        "linter": {
            "naming": {
                "enabled": True,
                "tenant_prefix": "",
                "bd_prefix": "",
                "epg_prefix": "",
                "contract_prefix": "",
                "ap_prefix": "",
            }
        },
    }

    # 3. config.yaml 저장
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)

        logger.info("config.yaml 저장 완료: %s", CONFIG_PATH)

        # ACIClient 재초기화 (main.py에서 주입된 콜백)
        if reinitialize_aci is not None:
            reinitialize_aci()
            logger.info("ACIClient 재초기화 완료")

    except OSError as e:
        logger.error("config.yaml 저장 실패: %s", e)
        return SetupResponse(
            success=False,
            message=f"파일 저장 실패: {e}",
        )

    return SetupResponse(
        success=True,
        message="설정이 저장되었습니다. 대시보드로 이동합니다.",
        connected_host=test_result.connected_host,
    )
