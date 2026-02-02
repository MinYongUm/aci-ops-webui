# ============================================
# Audit Log Router
# 목적: ACI 설정 변경 이력 데이터 제공
# ============================================

from fastapi import APIRouter

router = APIRouter()


def get_audit_data(aci):
    """
    Audit Log 데이터 조회 및 분석
    
    조회 항목:
    - 최근 설정 변경 이력
    - 변경 유형별 분류 (Creation/Modification/Deletion)
    - 사용자별 변경 횟수
    
    Args:
        aci: ACIClient 인스턴스
    Returns:
        dict: Audit Log 분석 결과 딕셔너리
    """
    # ============================================
    # 1. Audit Log 조회
    # ============================================
    # aaaModLR: 설정 변경 로그 클래스
    # order-by: 최신순 정렬
    # page-size: 최대 50개 조회
    logs = aci.get("aaaModLR", "order-by=aaaModLR.created|desc&page-size=50")
    
    # ============================================
    # 2. 변경 유형별 및 사용자별 집계
    # ============================================
    action_count = {"creation": 0, "modification": 0, "deletion": 0}
    user_count = {}
    recent_changes = []
    
    for log in logs:
        attr = log["aaaModLR"]["attributes"]
        
        # 변경 유형 (ind 속성)
        action = attr.get("ind", "")
        
        # 사용자
        user = attr.get("user", "unknown")
        
        # 유형별 카운트
        if action in action_count:
            action_count[action] += 1
        
        # 사용자별 카운트
        user_count[user] = user_count.get(user, 0) + 1
        
        # 최근 변경 목록에 추가
        recent_changes.append({
            "timestamp": attr.get("created", "")[:19],  # 초 단위까지만
            "user": user,
            "action": action,
            "affected": attr.get("affected", "")[:50]  # 50자로 제한
        })
    
    # ============================================
    # 3. 사용자별 통계를 리스트로 변환
    # ============================================
    by_user = [
        {"user": k, "count": v}
        for k, v in sorted(user_count.items(), key=lambda x: x[1], reverse=True)
    ]
    
    # ============================================
    # 4. 결과 반환
    # ============================================
    return {
        "total": len(logs),
        "actions": action_count,
        "by_user": by_user,
        "recent": recent_changes[:10]  # 최근 10개
    }