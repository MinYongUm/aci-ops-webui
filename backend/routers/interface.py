# ============================================
# Interface Monitor Router
# 목적: ACI 인터페이스 상태 모니터링 데이터 제공
# ============================================

from fastapi import APIRouter

router = APIRouter()


def get_interface_data(aci):
    """
    인터페이스 모니터링 데이터 조회 및 분석
    
    조회 항목:
    - 전체 인터페이스 수
    - Up/Down 개수
    - Down 원인별 분류
    
    Args:
        aci: ACIClient 인스턴스
    Returns:
        dict: 인터페이스 상태 딕셔너리
    """
    # ============================================
    # 1. 물리 인터페이스 상태 조회
    # ============================================
    # ethpmPhysIf: 물리 인터페이스 상태 클래스
    interfaces = aci.get("ethpmPhysIf")
    
    # ============================================
    # 2. Up/Down 분류 및 Down 원인 집계
    # ============================================
    up_count = 0
    down_count = 0
    down_reasons = {}  # 원인별 카운터
    
    for iface in interfaces:
        attr = iface["ethpmPhysIf"]["attributes"]
        
        if attr.get("operSt") == "up":
            up_count += 1
        else:
            down_count += 1
            # Down 원인 추출 (operStQual 속성)
            reason = attr.get("operStQual", "unknown")
            down_reasons[reason] = down_reasons.get(reason, 0) + 1
    
    # ============================================
    # 3. Down 원인을 리스트로 변환 (정렬)
    # ============================================
    # 카운트 많은 순으로 정렬
    down_reasons_list = [
        {"reason": k, "count": v}
        for k, v in sorted(down_reasons.items(), key=lambda x: x[1], reverse=True)
    ]
    
    # ============================================
    # 4. 결과 반환
    # ============================================
    return {
        "total": len(interfaces),
        "up": up_count,
        "down": down_count,
        "down_reasons": down_reasons_list
    }