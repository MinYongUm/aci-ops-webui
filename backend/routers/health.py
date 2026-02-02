# ============================================
# Health Check Router
# 목적: ACI Fabric 헬스 체크 데이터 제공
# ============================================

from fastapi import APIRouter

# FastAPI 라우터 인스턴스 생성
router = APIRouter()


def get_health_data(aci):
    """
    헬스 체크 데이터 조회 및 분석
    
    조회 항목:
    - Fault 목록 및 심각도별 분류
    - Critical/Major Fault 상세 정보
    - 노드 상태 (Up/Down)
    
    Args:
        aci: ACIClient 인스턴스
    Returns:
        dict: 헬스 체크 결과 딕셔너리
    """
    # ============================================
    # 1. Fault 조회 및 심각도별 분류
    # ============================================
    # faultInst: ACI Fault 클래스 (고정값)
    faults = aci.get("faultInst")
    
    # 심각도별 카운터 초기화
    severity_count = {"critical": 0, "major": 0, "minor": 0, "warning": 0}
    
    # Fault 순회하며 심각도별 집계
    for fault in faults:
        sev = fault["faultInst"]["attributes"].get("severity", "")
        if sev in severity_count:
            severity_count[sev] += 1
    
    # ============================================
    # 2. Critical/Major Fault 상세 정보 추출
    # ============================================
    critical_major = []
    for fault in faults:
        attr = fault["faultInst"]["attributes"]
        # Critical 또는 Major인 경우만 추가
        if attr.get("severity") in ["critical", "major"]:
            critical_major.append({
                "severity": attr.get("severity", "").upper(),
                "description": attr.get("descr", "")[:80]  # 80자로 제한
            })
    
    # ============================================
    # 3. 노드 상태 조회
    # ============================================
    # fabricNode: 모든 Fabric 노드 (Spine, Leaf, Controller)
    nodes = aci.get("fabricNode")
    
    # infraWiNode: Controller 상태 (별도 API)
    controllers = aci.get("infraWiNode")
    
    # Controller 상태를 딕셔너리로 저장 (이름 -> 상태)
    ctrl_status = {}
    for ctrl in controllers:
        attr = ctrl["infraWiNode"]["attributes"]
        ctrl_status[attr["nodeName"]] = attr.get("health", "unknown")
    
    # 노드별 Up/Down 카운트
    up_count = 0
    down_count = 0
    
    for node in nodes:
        attr = node["fabricNode"]["attributes"]
        role = attr.get("role", "")
        
        if role == "controller":
            # Controller는 infraWiNode의 health 값으로 판단
            health = ctrl_status.get(attr.get("name", ""), "unknown")
            status = "OK" if health == "fully-fit" else "DOWN"
        else:
            # Spine/Leaf는 fabricSt 값으로 판단
            status = "OK" if attr.get("fabricSt") == "active" else "DOWN"
        
        # 카운트 업데이트
        if status == "OK":
            up_count += 1
        else:
            down_count += 1
    
    # ============================================
    # 4. 결과 반환
    # ============================================
    return {
        "total_faults": len(faults),
        "severity": severity_count,
        "critical_major": critical_major[:10],  # 최대 10개
        "nodes": {
            "up": up_count,
            "down": down_count
        }
    }