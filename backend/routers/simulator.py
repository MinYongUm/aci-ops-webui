# ============================================
# Microsegmentation Simulator Router
# 목적: 시뮬레이션 API 엔드포인트
# 버전: v1.4.0
# ============================================

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.simulator_engine import SimulatorEngine, SimulationResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulate", tags=["simulate"])


# ============================================
# Request / Response 스키마
# ============================================


class SimulateRequest(BaseModel):
    """POST /api/simulate 요청 바디"""

    src_epg_dn: str
    dst_epg_dn: str


class FilterEntryOut(BaseModel):
    name: str
    ether_type: str
    ip_protocol: str
    dst_from_port: str
    dst_to_port: str


class SubjectOut(BaseModel):
    name: str
    filters: list[FilterEntryOut]


class ContractOut(BaseModel):
    name: str
    tenant: str
    dn: str
    subjects: list[SubjectOut]


class SimulateResponse(BaseModel):
    """POST /api/simulate 응답"""

    verdict: str
    src_epg: str
    dst_epg: str
    src_tenant: str
    dst_tenant: str
    matched_contracts: list[ContractOut]
    reason: str


# ============================================
# 엔드포인트
# ============================================


def get_simulate_router(aci) -> APIRouter:
    """
    aci 인스턴스를 주입받아 라우터 반환.
    main.py에서 호출.

    Args:
        aci: ACIClient 인스턴스
    Returns:
        APIRouter
    """
    engine = SimulatorEngine(aci)

    @router.get("/tenants", summary="Tenant 목록 조회 (드롭다운용)")
    async def get_tenants() -> list[dict]:
        """
        사용자 Tenant 목록 반환.
        시스템 Tenant (common, infra, mgmt) 제외.
        """
        try:
            return engine.get_tenants()
        except Exception as exc:
            logger.exception("Tenant 목록 조회 실패")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/epgs", summary="EPG 목록 조회 (드롭다운용)")
    async def get_epgs(tenant: Optional[str] = None) -> list[dict]:
        """
        EPG 목록 반환.

        Query Params:
            tenant: Tenant 이름으로 필터링 (생략 시 전체)
        """
        try:
            return engine.get_epgs(tenant)
        except Exception as exc:
            logger.exception("EPG 목록 조회 실패")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("", summary="트래픽 허용/차단 시뮬레이션")
    async def simulate(body: SimulateRequest) -> SimulateResponse:
        """
        Source EPG → Destination EPG 트래픽 가능 여부 판정.

        - Consumer(src) / Provider(dst) 방향으로 Contract 탐색
        - ACI Whitelist 모델 기준: 명시적 허용 없으면 Deny-All
        """
        if not body.src_epg_dn or not body.dst_epg_dn:
            raise HTTPException(
                status_code=400, detail="src_epg_dn과 dst_epg_dn은 필수 항목입니다."
            )

        if body.src_epg_dn == body.dst_epg_dn:
            raise HTTPException(
                status_code=400, detail="Source EPG와 Destination EPG가 동일합니다."
            )

        try:
            result: SimulationResult = engine.simulate(
                src_epg_dn=body.src_epg_dn, dst_epg_dn=body.dst_epg_dn
            )
        except Exception as exc:
            logger.exception("시뮬레이션 실행 실패")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        # SimulationResult → SimulateResponse 변환
        contracts_out = [
            ContractOut(
                name=c.name,
                tenant=c.tenant,
                dn=c.dn,
                subjects=[
                    SubjectOut(
                        name=s.name,
                        filters=[
                            FilterEntryOut(
                                name=f.name,
                                ether_type=f.ether_type,
                                ip_protocol=f.ip_protocol,
                                dst_from_port=f.dst_from_port,
                                dst_to_port=f.dst_to_port,
                            )
                            for f in s.filters
                        ],
                    )
                    for s in c.subjects
                ],
            )
            for c in result.matched_contracts
        ]

        return SimulateResponse(
            verdict=result.verdict,
            src_epg=result.src_epg,
            dst_epg=result.dst_epg,
            src_tenant=result.src_tenant,
            dst_tenant=result.dst_tenant,
            matched_contracts=contracts_out,
            reason=result.reason,
        )

    return router
