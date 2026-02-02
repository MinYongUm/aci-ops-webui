# ============================================
# ACI Ops WebUI - Backend Main
# 목적: FastAPI 애플리케이션 진입점
# 
# 실행 방법:
#   cd backend
#   uvicorn main:app --reload --host 0.0.0.0 --port 8000
# ============================================

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sys
import os

# ============================================
# 경로 설정
# - 현재 파일 기준으로 모듈 import 경로 추가
# ============================================
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ============================================
# 모듈 import
# - ACI 클라이언트: APIC 연결 관리
# - 각 라우터: API 엔드포인트별 데이터 처리 함수
# ============================================
from services.aci_client import ACIClient
from routers.health import get_health_data
from routers.policy import get_policy_data
from routers.interface import get_interface_data
from routers.endpoint import get_endpoint_data
from routers.audit import get_audit_data
from routers.capacity import get_capacity_data
from routers.topology import get_topology_data

# ============================================
# FastAPI 앱 인스턴스 생성
# ============================================
app = FastAPI(
    title="ACI Ops WebUI",      # API 문서 제목
    version="1.0.0"             # 버전
)

# ============================================
# ACI 클라이언트 초기화
# - 앱 시작 시 한 번만 생성
# - 모든 API 요청에서 공유
# ============================================
aci = ACIClient()

# ============================================
# Static 파일 서빙 설정
# - /static 경로로 frontend 폴더 파일 제공
# - CSS, JS, 이미지 등 정적 파일 접근용
# ============================================
app.mount("/static", StaticFiles(directory="../frontend"), name="static")


# ============================================
# API 엔드포인트 정의
# ============================================

@app.get("/")
async def root():
    """
    메인 페이지 (루트 경로)
    
    - index.html 파일 반환
    - 브라우저에서 대시보드 표시
    """
    return FileResponse("../frontend/index.html")


@app.get("/api/health")
async def api_health():
    """
    Health Check API
    
    - Fault 현황
    - 노드 상태
    
    Returns:
        dict: 헬스 체크 결과
    """
    return get_health_data(aci)


@app.get("/api/policy")
async def api_policy():
    """
    Policy Check API
    
    - Tenant, Contract, Filter 통계
    - 보안 위험 감지
    
    Returns:
        dict: 정책 검증 결과
    """
    return get_policy_data(aci)


@app.get("/api/interface")
async def api_interface():
    """
    Interface Monitor API
    
    - 인터페이스 Up/Down 현황
    - Down 원인 분석
    
    Returns:
        dict: 인터페이스 상태
    """
    return get_interface_data(aci)


@app.get("/api/endpoint")
async def api_endpoint():
    """
    Endpoint Tracker API
    
    - 전체 Endpoint 수
    - Tenant별 통계
    
    Returns:
        dict: Endpoint 통계
    """
    return get_endpoint_data(aci)


@app.get("/api/audit")
async def api_audit():
    """
    Audit Log API
    
    - 최근 설정 변경 이력
    - 변경 유형별, 사용자별 통계
    
    Returns:
        dict: Audit Log 분석 결과
    """
    return get_audit_data(aci)


@app.get("/api/capacity")
async def api_capacity():
    """
    Capacity Report API
    
    - TCAM 사용량
    - 고사용률 노드 감지
    
    Returns:
        dict: 용량 리포트
    """
    return get_capacity_data(aci)


@app.get("/api/topology")
async def api_topology():
    """
    Topology Viewer API
    
    - Controller, Spine, Leaf 노드 목록
    - 노드 상태 정보
    
    Returns:
        dict: 토폴로지 데이터
    """
    return get_topology_data(aci)


@app.get("/api/all")
async def api_all():
    """
    전체 리포트 API
    
    - 모든 모듈 데이터를 한 번에 조회
    - 대시보드 초기 로딩 시 사용
    
    Returns:
        dict: 모든 모듈 데이터 통합
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