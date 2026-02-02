# ============================================
# Endpoint Tracker Router
# 목적: ACI Endpoint 추적 데이터 제공
# ============================================

from fastapi import APIRouter

router = APIRouter()


def get_endpoint_data(aci):
    """
    Endpoint 추적 데이터 조회 및 분석
    
    조회 항목:
    - 전체 Endpoint 수
    - Tenant별 Endpoint 개수
    
    Args:
        aci: ACIClient 인스턴스
    Returns:
        dict: Endpoint 통계 딕셔너리
    """
    # ============================================
    # 1. Endpoint 목록 조회
    # ============================================
    # fvCEp: Client Endpoint 클래스
    endpoints = aci.get("fvCEp")
    
    # ============================================
    # 2. Tenant별 Endpoint 집계
    # ============================================
    tenant_count = {}
    
    for ep in endpoints:
        # DN에서 Tenant 이름 추출
        # 예: uni/tn-TENANT/ap-APP/epg-EPG/cep-MAC
        dn = ep["fvCEp"]["attributes"].get("dn", "")
        parts = dn.split("/")
        tenant = parts[1].replace("tn-", "") if len(parts) > 1 else "unknown"
        
        # 카운트 증가
        tenant_count[tenant] = tenant_count.get(tenant, 0) + 1
    
    # ============================================
    # 3. 리스트로 변환 (정렬)
    # ============================================
    # Endpoint 많은 순으로 정렬, 상위 10개
    by_tenant = [
        {"tenant": k, "count": v}
        for k, v in sorted(tenant_count.items(), key=lambda x: x[1], reverse=True)
    ]
    
    # ============================================
    # 4. 결과 반환
    # ============================================
    return {
        "total": len(endpoints),
        "by_tenant": by_tenant[:10]
    }