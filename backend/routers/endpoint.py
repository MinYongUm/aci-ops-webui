# ============================================
# Endpoint Tracker Router
# 목적: ACI Endpoint 추적 데이터 제공
# 버전: v1.1.0 - 검색 기능 추가
# ============================================

import re
from fastapi import APIRouter

router = APIRouter()


def get_endpoint_data(aci):
    """
    Endpoint 추적 데이터 조회 및 분석
    
    Args:
        aci: ACIClient 인스턴스
    Returns:
        dict: Endpoint 통계 딕셔너리
    """
    # fvCEp: Client Endpoint 클래스
    endpoints = aci.get("fvCEp")
    
    # Tenant별 집계
    tenant_count = {}
    for ep in endpoints:
        dn = ep["fvCEp"]["attributes"].get("dn", "")
        parts = dn.split("/")
        tenant = parts[1].replace("tn-", "") if len(parts) > 1 else "unknown"
        tenant_count[tenant] = tenant_count.get(tenant, 0) + 1
    
    # 정렬 후 상위 10개
    by_tenant = [
        {"tenant": k, "count": v}
        for k, v in sorted(tenant_count.items(), key=lambda x: x[1], reverse=True)
    ]
    
    return {
        "total": len(endpoints),
        "by_tenant": by_tenant[:10]
    }


def search_endpoint(aci, query):
    """
    Endpoint 검색 (MAC 또는 IP)
    
    - MAC 주소 또는 IP 주소로 Endpoint 검색
    - 연결된 Node, Interface 정보 포함
    
    Args:
        aci: ACIClient 인스턴스
        query: 검색어 (MAC 또는 IP)
    Returns:
        list: 검색된 Endpoint 목록
    """
    # 전체 Endpoint 조회
    endpoints = aci.get("fvCEp")
    
    # Endpoint 경로 정보 조회
    paths = aci.get("fvRsCEpToPathEp")
    
    # 검색어 정규화 (소문자, 하이픈→콜론)
    query_normalized = query.lower().replace("-", ":")
    
    results = []
    
    for ep in endpoints:
        attr = ep["fvCEp"]["attributes"]
        mac = attr.get("mac", "").lower()
        ip = attr.get("ip", "")
        dn = attr.get("dn", "")
        
        # ============================================
        # MAC 또는 IP 매칭 확인
        # ============================================
        if query_normalized in mac or query in ip:
            
            # DN에서 Tenant, AP, EPG 추출
            tenant = "unknown"
            app = "unknown"
            epg = "unknown"
            
            parts = dn.split("/")
            for part in parts:
                if part.startswith("tn-"):
                    tenant = part.replace("tn-", "")
                elif part.startswith("ap-"):
                    app = part.replace("ap-", "")
                elif part.startswith("epg-"):
                    epg = part.replace("epg-", "")
            
            # ============================================
            # 경로 정보 찾기 (Node, Interface)
            # ============================================
            node = "-"
            interface = "-"
            
            for path in paths:
                path_dn = path["fvRsCEpToPathEp"]["attributes"].get("dn", "")
                
                # 현재 Endpoint의 경로인지 확인
                if dn in path_dn:
                    tdn = path["fvRsCEpToPathEp"]["attributes"].get("tDn", "")
                    
                    # 노드 ID 추출 (정규식)
                    node_match = re.search(r'paths-(\d+)', tdn)
                    if node_match:
                        node = node_match.group(1)
                    
                    # 인터페이스 추출 (정규식)
                    iface_match = re.search(r'\[(.+)\]', tdn)
                    if iface_match:
                        interface = iface_match.group(1)
                    break
            
            # 결과 추가
            results.append({
                "mac": attr.get("mac", ""),
                "ip": ip if ip else "-",
                "tenant": tenant,
                "app_profile": app,
                "epg": epg,
                "encap": attr.get("encap", ""),
                "node": node,
                "interface": interface
            })
    
    return results