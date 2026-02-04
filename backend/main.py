# ============================================
# ACI Ops WebUI - Backend Main
# 목적: FastAPI 애플리케이션 진입점
# 버전: v1.1.0 - Endpoint 검색 API 추가
#
# 실행 방법:
#   cd backend
#   uvicorn main:app --reload --host 0.0.0.0 --port 8000
# ============================================

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sys
import os

# ============================================
# 경로 설정
# ============================================
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ============================================
# 모듈 import
# ============================================
from services.aci_client import ACIClient
from routers.health import get_health_data
from routers.policy import get_policy_data
from routers.interface import get_interface_data
from routers.endpoint import get_endpoint_data, search_endpoint
from routers.audit import get_audit_data
from routers.capacity import get_capacity_data
from routers.topology import get_topology_data

# ============================================
# FastAPI 앱 인스턴스 생성
# ============================================
app = FastAPI(
    title="ACI Ops WebUI",
    version="1.1.0"
)

# ============================================
# ACI 클라이언트 초기화
# ============================================
aci = ACIClient()

# ============================================
# Static 파일 서빙 설정
# ============================================
app.mount("/static", StaticFiles(directory="../frontend"), name="static")


# ============================================
# API 엔드포인트 정의
# ============================================

@app.get("/")
async def root():
    """메인 페이지"""
    return FileResponse("../frontend/index.html")


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
    Endpoint 검색 API (v1.1.0 추가)
    
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


@app.get("/api/all")
async def api_all():
    """
    전체 리포트 API
    
    - 모든 모듈 데이터를 한 번에 조회
    - 대시보드 초기 로딩 시 사용
    """
    return {
        "health": get_health_data(aci),
        "policy": get_policy_data(aci),
        "interface": get_interface_data(aci),
        "endpoint": get_endpoint_data(aci),
        "audit": get_audit_data(aci),
        "capacity": get_capacity_data(aci),
        "topology": get_topology_data(aci)
    }