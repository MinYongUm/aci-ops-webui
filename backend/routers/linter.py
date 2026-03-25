# ============================================
# ACI Config Linter Router
# 목적: Config Linter API 엔드포인트 제공
# 버전: v1.3.0
#
# 엔드포인트:
#   GET  /api/lint            — APIC Live 조회 후 Linter 실행
#   POST /api/lint/upload     — JSON 파일 업로드 후 Linter 실행
# ============================================

import json
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File

from services.linter_engine import LinterService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_lint_data(aci) -> dict:
    """
    APIC Live 조회 기반 Linter 실행

    GET /api/lint 핸들러에서 호출.
    main.py의 ACIClient 인스턴스를 그대로 전달받아 사용.

    Args:
        aci: ACIClient 인스턴스
    Returns:
        dict: Linter 결과 (source, total_issues, summary, results)
    Raises:
        HTTPException 500: Linter 실행 중 예외 발생 시
    """
    try:
        service = LinterService()
        return service.run_live(aci)
    except Exception as exc:
        logger.error("Live lint failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Linter execution failed: {exc}",
        )


async def lint_upload(file: UploadFile) -> dict:
    """
    업로드 파일 기반 Linter 실행

    POST /api/lint/upload 핸들러에서 호출.
    파일을 메모리에서 직접 파싱 — 디스크 저장 없음.

    Args:
        file: FastAPI UploadFile (multipart/form-data)
    Returns:
        dict: Linter 결과 (source, total_issues, summary, results)
    Raises:
        HTTPException 400: 파일 형식 오류 또는 JSON 파싱 실패
        HTTPException 500: Linter 실행 중 예외 발생 시
    """
    # ============================================
    # 1. 파일 확장자 검증
    # ============================================
    filename: str = file.filename or ""
    if not filename.endswith(".json"):
        raise HTTPException(
            status_code=400,
            detail="Only .json files are accepted",
        )

    # ============================================
    # 2. 파일 내용 읽기 및 JSON 파싱
    # ============================================
    try:
        raw_bytes: bytes = await file.read()
        file_content: dict = json.loads(raw_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error for file '%s': %s", filename, exc)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON format: {exc}",
        )
    except Exception as exc:
        logger.error("File read error: %s", exc)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read file: {exc}",
        )

    # ============================================
    # 3. Linter 실행
    # ============================================
    try:
        service = LinterService()
        return service.run_from_file(file_content)
    except Exception as exc:
        logger.error("File-based lint failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Linter execution failed: {exc}",
        )