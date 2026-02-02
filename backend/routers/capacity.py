# ============================================
# Capacity Report Router
# 목적: ACI 용량 리포트 데이터 제공
# ============================================

import re
from fastapi import APIRouter

router = APIRouter()


def get_capacity_data(aci):
    """
    용량 리포트 데이터 조회 및 분석
    
    조회 항목:
    - TCAM (Policy CAM) 사용량
    - 노드별 사용률
    - 고사용률 노드 (>=80%) 감지
    
    Args:
        aci: ACIClient 인스턴스
    Returns:
        dict: 용량 리포트 딕셔너리
    """
    # ============================================
    # 1. 노드 ID -> 이름 매핑 테이블 생성
    # ============================================
    nodes = aci.get("fabricNode")
    node_map = {}
    for node in nodes:
        attr = node["fabricNode"]["attributes"]
        # ID와 이름 매핑 저장
        node_map[attr.get("id", "")] = attr.get("name", "")
    
    # ============================================
    # 2. TCAM 사용량 조회
    # ============================================
    # eqptcapacityPolUsage5min: Policy CAM 사용량 클래스 (5분 평균)
    tcam_data = aci.get("eqptcapacityPolUsage5min")
    
    # ============================================
    # 3. 노드별 사용량 분석
    # ============================================
    tcam_usage = []
    high_usage_count = 0  # 고사용률 노드 카운터
    
    for item in tcam_data:
        attr = item["eqptcapacityPolUsage5min"]["attributes"]
        dn = attr.get("dn", "")
        
        # DN에서 노드 ID 추출 (정규식 사용)
        match = re.search(r'node-(\d+)', dn)
        node_id = match.group(1) if match else "unknown"
        
        # 노드 이름 조회
        node_name = node_map.get(node_id, node_id)
        
        # 사용량 계산
        used = int(attr.get("polUsageCum", 0))
        cap = int(attr.get("polUsageCapCum", 1))  # 0으로 나누기 방지
        
        # 사용률 계산 (퍼센트)
        pct = round((used / cap) * 100, 1) if cap > 0 else 0
        
        # 고사용률 체크 (80% 이상)
        if pct >= 80:
            high_usage_count += 1
        
        # 결과 추가
        tcam_usage.append({
            "node": node_name,
            "used": used,
            "capacity": cap,
            "percentage": pct
        })
    
    # ============================================
    # 4. 사용률 높은 순으로 정렬
    # ============================================
    tcam_usage.sort(key=lambda x: x["percentage"], reverse=True)
    
    # ============================================
    # 5. 결과 반환
    # ============================================
    return {
        "high_usage_count": high_usage_count,
        "tcam": tcam_usage[:15]  # 상위 15개
    }