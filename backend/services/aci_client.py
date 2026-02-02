# ============================================
# ACI API Client
# 목적: ACI APIC 연결 및 API 호출 공통 모듈
# ============================================

import requests
import yaml

# SSL 인증서 경고 메시지 비활성화 (Self-signed 인증서 사용 시)
requests.packages.urllib3.disable_warnings()


class ACIClient:
    """
    ACI APIC API 클라이언트 클래스
    
    - APIC 로그인 및 세션 관리
    - REST API 호출 공통 메서드 제공
    - 모든 모듈에서 공유하여 사용
    """
    
    def __init__(self, config_path="config.yaml"):
        """
        클라이언트 초기화
        
        Args:
            config_path: 설정 파일 경로 (기본값: config.yaml)
        """
        # 설정 파일 로드
        self.config = self._load_config(config_path)
        
        # APIC 호스트 주소 저장
        self.apic = self.config["apic"]["host"]
        
        # requests 세션 생성 (쿠키, 인증 토큰 자동 관리)
        self.session = requests.Session()
        
        # 로그인 상태 플래그
        self.logged_in = False
    
    def _load_config(self, config_path):
        """
        설정 파일 로드 (Private 메서드)
        
        Args:
            config_path: YAML 설정 파일 경로
        Returns:
            dict: 설정값 딕셔너리
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def login(self):
        """
        APIC 로그인
        
        - aaaUser: ACI 인증 클래스 (고정값)
        - aaaLogin.json: 로그인 엔드포인트 (고정값)
        - 로그인 성공 시 세션에 토큰 자동 저장됨
        
        Returns:
            bool: 로그인 성공 여부
        """
        # ACI 인증 요청 본문 구성
        auth = {
            "aaaUser": {
                "attributes": {
                    "name": self.config["apic"]["username"],
                    "pwd": self.config["apic"]["password"]
                }
            }
        }
        
        # 로그인 API 호출
        resp = self.session.post(
            f"{self.apic}/api/aaaLogin.json",
            json=auth,
            verify=False  # SSL 인증서 검증 비활성화
        )
        
        # 로그인 상태 업데이트
        self.logged_in = resp.ok
        return resp.ok
    
    def get(self, class_name, query=""):
        """
        ACI API GET 요청 공통 메서드
        
        - 로그인 안 되어 있으면 자동 로그인
        - 클래스 기반 쿼리 (Class-level query)
        
        Args:
            class_name: ACI 클래스명 (예: faultInst, fabricNode 등)
            query: 추가 쿼리 파라미터 (옵션)
        Returns:
            list: API 응답의 imdata 배열
        """
        # 로그인 상태 확인 및 자동 로그인
        if not self.logged_in:
            self.login()
        
        # API URL 구성
        url = f"{self.apic}/api/class/{class_name}.json"
        
        # 쿼리 파라미터가 있으면 추가
        if query:
            url += f"?{query}"
        
        # GET 요청 실행
        resp = self.session.get(url, verify=False)
        
        # imdata 배열 반환 (없으면 빈 배열)
        return resp.json().get("imdata", [])