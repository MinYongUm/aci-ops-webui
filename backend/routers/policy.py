# ============================================
# Policy Check Router
# 목적: ACI 정책 검증 및 보안 감사 데이터 제공
# ============================================

from fastapi import APIRouter

router = APIRouter()


def get_policy_data(aci):
    """
    정책 검증 데이터 조회 및 분석
    
    조회 항목:
    - Tenant, Contract, Filter 개수
    - 위험한 Contract/Filter 감지 (PermitAll 등)
    
    Args:
        aci: ACIClient 인스턴스
    Returns:
        dict: 정책 검증 결과 딕셔너리
    """
    # ============================================
    # 1. 기본 정보 조회
    # ============================================
    # fvTenant: Tenant 클래스
    tenants = aci.get("fvTenant")
    
    # vzBrCP: Contract 클래스
    contracts = aci.get("vzBrCP")
    
    # vzFilter: Filter 클래스
    filters = aci.get("vzFilter")
    
    # ============================================
    # 2. 위험한 정책 감지
    # ============================================
    # 보안상 위험한 키워드 목록
    risky_keywords = ["permitall", "permit_all", "allow_all", "allowall"]
    
    risky_contracts = []
    risky_filters = []
    
    # Contract 검사
    for contract in contracts:
        attr = contract["vzBrCP"]["attributes"]
        name = attr.get("name", "").lower()
        
        # 위험 키워드 포함 여부 확인
        if any(k in name for k in risky_keywords):
            # DN에서 Tenant 이름 추출
            dn = attr.get("dn", "")
            parts = dn.split("/")
            tenant = parts[1].replace("tn-", "") if len(parts) > 1 else "unknown"
            
            risky_contracts.append({
                "tenant": tenant,
                "name": attr.get("name", "")
            })
    
    # Filter 검사
    for f in filters:
        attr = f["vzFilter"]["attributes"]
        name = attr.get("name", "").lower()
        
        if any(k in name for k in risky_keywords):
            dn = attr.get("dn", "")
            parts = dn.split("/")
            tenant = parts[1].replace("tn-", "") if len(parts) > 1 else "unknown"
            
            risky_filters.append({
                "tenant": tenant,
                "name": attr.get("name", "")
            })
    
    # ============================================
    # 3. 결과 반환
    # ============================================
    return {
        "total_tenants": len(tenants),
        "total_contracts": len(contracts),
        "total_filters": len(filters),
        "security_risks": len(risky_contracts) + len(risky_filters),
        "risky_contracts": risky_contracts,
        "risky_filters": risky_filters
    }