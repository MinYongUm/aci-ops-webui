# ============================================
# ACI API Client
# 목적: ACI APIC 연결 및 API 호출 공통 모듈
# 버전: v1.7.0 - login() Race Condition 수정 (threading.Lock)
# ============================================

import logging
import threading
from typing import List

import requests
import yaml

# SSL 인증서 경고 메시지 비활성화 (Self-signed 인증서 사용 시)
requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)


class ACIClient:
    """
    ACI APIC API 클라이언트 클래스

    - APIC 로그인 및 세션 관리 (Failover 포함)
    - REST API 호출 공통 메서드 제공
    - timeout / retry 횟수 config.yaml에서 설정
    - 모든 모듈에서 공유하여 사용

    v1.7.0 변경사항:
    - _login_lock (threading.Lock) 추가
    - /api/all 병렬 호출 시 세션 만료 Race Condition 해결
      → 첫 번째 스레드가 login() 완료 후 나머지 스레드는
        logged_in=True 확인 후 즉시 통과
    """

    def __init__(self, config_path: str = "config.yaml") -> None:
        """
        클라이언트 초기화

        Args:
            config_path: 설정 파일 경로 (기본값: config.yaml)
        """
        # 설정 파일 로드
        self.config = self._load_config(config_path)

        # ============================================
        # APIC hosts 리스트 로드 (v1.5.0)
        # 단독(1대): hosts에 1개 / 클러스터(3대): hosts에 3개
        # Primary -> Failover 순으로 순서 입력
        # ============================================
        self.hosts: List[str] = self.config["apic"]["hosts"]

        # 현재 연결된 APIC 주소 (login() 성공 시 갱신)
        self.apic: str = self.hosts[0]

        # timeout / retry 설정 (config.yaml에서 읽기, 없으면 기본값 사용)
        self.timeout: int = self.config["apic"].get("timeout", 30)
        self.retry: int = self.config["apic"].get("retry", 3)

        # requests 세션 생성 (쿠키, 인증 토큰 자동 관리)
        self.session = requests.Session()

        # 로그인 상태 플래그
        self.logged_in: bool = False

        # ============================================
        # v1.7.0: login() 직렬화 Lock
        # /api/all의 ThreadPoolExecutor 병렬 호출 시
        # 세션 만료(401)를 여러 스레드가 동시에 감지해도
        # login()은 반드시 1개 스레드만 실행되도록 보장
        # ============================================
        self._login_lock = threading.Lock()

    def _load_config(self, config_path: str) -> dict:
        """
        설정 파일 로드 (Private 메서드)

        Args:
            config_path: YAML 설정 파일 경로
        Returns:
            dict: 설정값 딕셔너리
        """
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def login(self) -> bool:
        """
        APIC 로그인 (Failover 포함, Lock으로 직렬화)

        v1.7.0: _login_lock으로 동시 호출을 직렬화합니다.
        Lock 대기 후 진입 시 이미 logged_in=True이면
        다른 스레드가 로그인을 완료한 것이므로 즉시 True 반환합니다.

        hosts 리스트를 순서대로 시도합니다.
        Primary 연결 실패 시 다음 host로 자동 전환합니다.

        Returns:
            bool: 로그인 성공 여부 (전체 host 실패 시 False)
        """
        with self._login_lock:
            # ============================================
            # Lock 획득 후 재확인 (Double-Checked Locking)
            # 대기 중 다른 스레드가 이미 로그인 완료했으면 통과
            # ============================================
            if self.logged_in:
                return True

            # ACI 인증 요청 본문 구성
            auth = {
                "aaaUser": {
                    "attributes": {
                        "name": self.config["apic"]["username"],
                        "pwd": self.config["apic"]["password"],
                    }
                }
            }

            # ============================================
            # hosts 리스트 순서대로 Failover 시도
            # Static Route next-hop 순차 시도와 동일한 개념
            # ============================================
            for host in self.hosts:
                try:
                    logger.info("APIC 로그인 시도: %s", host)

                    resp = self.session.post(
                        f"{host}/api/aaaLogin.json",
                        json=auth,
                        verify=False,
                        timeout=self.timeout,
                    )

                    if resp.ok:
                        # 로그인 성공 → 현재 APIC 주소 갱신
                        self.apic = host
                        self.logged_in = True
                        logger.info("APIC 로그인 성공: %s", host)
                        return True

                    logger.warning(
                        "APIC 로그인 실패 (HTTP %s): %s", resp.status_code, host
                    )

                except requests.exceptions.Timeout:
                    logger.warning(
                        "APIC 연결 타임아웃 (%ds): %s", self.timeout, host
                    )

                except requests.exceptions.ConnectionError:
                    logger.warning("APIC 연결 오류 (ConnectionError): %s", host)

            # 모든 host 실패
            self.logged_in = False
            logger.error("모든 APIC host 로그인 실패: %s", self.hosts)
            return False

    def _get_once(self, class_name: str, query: str = "") -> list:
        """
        ACI API GET 요청 1회 실행 (내부 메서드)

        Args:
            class_name: ACI 클래스명
            query: 추가 쿼리 파라미터 (옵션)
        Returns:
            list: imdata 배열 (class_name 키 없는 항목 필터링 완료)
        Raises:
            requests.exceptions.Timeout: 타임아웃 발생 시
            requests.exceptions.ConnectionError: 연결 오류 발생 시
        """
        url = f"{self.apic}/api/class/{class_name}.json"

        if query:
            url += f"?{query}"

        resp = self.session.get(url, verify=False, timeout=self.timeout)

        # 401: 세션 만료 — 호출자(get)에서 재로그인 처리
        if resp.status_code == 401:
            logger.warning("APIC 세션 만료 (401). 재로그인 시도합니다.")
            self.logged_in = False
            raise requests.exceptions.ConnectionError("session_expired")

        # imdata 반환, class_name 키 없는 항목(error 오브젝트 등) 필터링
        return [item for item in resp.json().get("imdata", []) if class_name in item]

    def get(self, class_name: str, query: str = "") -> list:
        """
        ACI API GET 요청 공통 메서드

        - 로그인 안 되어 있으면 자동 로그인
        - Timeout / ConnectionError 발생 시 Failover 재시도
        - 세션 만료(401) 시 자동 재로그인 후 1회 재시도
        - 클래스 기반 쿼리 (Class-level query)

        Args:
            class_name: ACI 클래스명 (예: faultInst, fabricNode 등)
            query: 추가 쿼리 파라미터 (옵션)
        Returns:
            list: API 응답의 imdata 배열 (실패 시 빈 배열)
        """
        # 로그인 상태 확인 및 자동 로그인
        if not self.logged_in:
            if not self.login():
                logger.error("로그인 실패로 API 조회 불가: %s", class_name)
                return []

        # ============================================
        # retry 횟수만큼 재시도 (Failover + 세션 재로그인 포함)
        # ============================================
        for attempt in range(1, self.retry + 1):
            try:
                return self._get_once(class_name, query)

            except requests.exceptions.Timeout:
                logger.warning(
                    "API 타임아웃 (시도 %d/%d) class=%s host=%s",
                    attempt,
                    self.retry,
                    class_name,
                    self.apic,
                )
                # 다음 시도 전 Failover 로그인 시도
                if not self.login():
                    logger.error("Failover 로그인 실패. 빈 배열 반환.")
                    return []

            except requests.exceptions.ConnectionError as exc:
                if "session_expired" in str(exc):
                    # 세션 만료 → 재로그인 후 재시도
                    logger.info(
                        "세션 재로그인 시도 (attempt %d/%d)",
                        attempt,
                        self.retry,
                    )
                    if not self.login():
                        logger.error("재로그인 실패. 빈 배열 반환.")
                        return []
                else:
                    logger.warning(
                        "연결 오류 (시도 %d/%d) class=%s host=%s",
                        attempt,
                        self.retry,
                        class_name,
                        self.apic,
                    )
                    if not self.login():
                        logger.error("Failover 로그인 실패. 빈 배열 반환.")
                        return []

            except Exception as exc:
                logger.error("예상치 못한 오류 class=%s: %s", class_name, exc)
                return []

        logger.error(
            "최대 재시도 횟수 초과 (%d회). 빈 배열 반환. class=%s",
            self.retry,
            class_name,
        )
        return []