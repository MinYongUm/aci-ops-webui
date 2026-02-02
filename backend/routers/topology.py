# ============================================
# Topology Viewer Router
# 목적: ACI Fabric 토폴로지 데이터 제공
# ============================================

from fastapi import APIRouter

router = APIRouter()


def get_topology_data(aci):
    """
    토폴로지 데이터 조회 및 분석
    
    조회 항목:
    - Fabric 노드 목록 (Controller, Spine, Leaf)
    - 노드별 상세 정보 (ID, 이름, 모델, 상태)
    
    Args:
        aci: ACIClient 인스턴스
    Returns:
        dict: 토폴로지 데이터 딕셔너리
    """
    # ============================================
    # 1. Fabric 노드 목록 조회
    # ============================================
    # fabricNode: 모든 Fabric 노드 클래스
    nodes = aci.get("fabricNode")
    
    # ============================================
    # 2. 역할별 노드 분류
    # ============================================
    spines = []
    leafs = []
    controllers = []
    
    for node in nodes:
        attr = node["fabricNode"]["attributes"]
        
        # 노드 정보 추출
        info = {
            "id": attr.get("id", ""),
            "name": attr.get("name", ""),
            "model": attr.get("model", ""),
            # 상태 판단: active면 UP, 아니면 DOWN
            # Controller는 fabricSt가 없으므로 기본 UP 처리
            "status": "UP" if attr.get("fabricSt") == "active" or attr.get("role") == "controller" else "DOWN"
        }
        
        # 역할에 따라 분류
        role = attr.get("role", "")
        if role == "spine":
            spines.append(info)
        elif role == "leaf":
            leafs.append(info)
        elif role == "controller":
            controllers.append(info)
    
    # ============================================
    # 3. ID 순으로 정렬
    # ============================================
    spines.sort(key=lambda x: int(x["id"]))
    leafs.sort(key=lambda x: int(x["id"]))
    controllers.sort(key=lambda x: int(x["id"]))
    
    # ============================================
    # 4. 결과 반환
    # ============================================
    return {
        "summary": {
            "controllers": len(controllers),
            "spines": len(spines),
            "leafs": len(leafs)
        },
        "controllers": controllers,
        "spines": spines,
        "leafs": leafs
    }