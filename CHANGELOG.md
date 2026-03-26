# Changelog

## [1.5.0] - 2026-03-26
### Added
- APIC Failover: config.yaml `hosts` 리스트 구조 도입
  - Primary APIC 연결 실패 시 다음 host로 자동 전환
  - 단독(1대) / 클러스터(3대) 혼재 환경 모두 지원
- ACIClient 에러핸들링 강화
  - `timeout` / `retry` 횟수 config.yaml에서 설정 가능
  - Timeout / ConnectionError 발생 시 Failover 재시도
  - 세션 만료(401) 감지 후 자동 재로그인 및 1회 재시도
  - 전체 host 실패 시 빈 배열 반환 (예외 미전파)
- `/api/all` 병렬 처리: ThreadPoolExecutor 도입
  - 7개 모듈 동시 조회 → 응답 시간 단축
  - `max_workers=len(tasks)`: 모듈 추가/제거 시 자동 반영
  - 모듈 단위 예외 발생 시 해당 모듈만 None 반환 (전체 실패 방지)
- TestACIClientFailover 테스트 클래스 추가 (3개)
  - test_failover_on_first_host_down
  - test_all_hosts_down_returns_empty
  - test_session_expired_relogin

### Changed
- config.yaml.example: `host` (단수) → `hosts` (리스트) 구조 변경, timeout/retry 항목 추가
- aci_client.py: `_get_once()` 내부 메서드 분리, 타입 힌트 전면 적용
- main.py: 버전 v1.5.0 반영, linter 엔드포인트 직접 정의 방식으로 통일
- conftest.py: `_RealACIClient` 저장 추가 (Failover 테스트 지원)
- .flake8: tests/conftest.py E402 예외 추가

### Test
- 61 passed, 1 skipped (v1.4.0 대비 +3)

## [1.4.0] - 2026-03-26
### Added
- Microsegmentation Simulator 기능 추가
  - GET /api/simulate/tenants: Tenant 목록 조회 (드롭다운용, 시스템 Tenant 제외)
  - GET /api/simulate/epgs?tenant=: Tenant별 EPG 목록 조회
  - POST /api/simulate: EPG 간 트래픽 허용/차단 판정 (ACI Whitelist 모델 기준)
- backend/services/simulator_engine.py: 시뮬레이션 엔진 (SimulatorDataCollector, SimulatorEngine)
  - EpgInfo, ContractInfo, SubjectInfo, FilterEntry, SimulationResult 데이터 클래스
  - Consumer/Provider Contract 교집합 탐색 → ALLOW / DENY 판정
- backend/routers/simulator.py: 시뮬레이터 API 엔드포인트 (팩토리 패턴 get_simulate_router)
- frontend/index.html: Microsegmentation Simulator 섹션 UI 추가
  - Source / Destination EPG 2단계 드롭다운 (Tenant → EPG)
  - ALLOW / DENY 판정 배지 + 판정 근거 텍스트
  - SVG 경로 다이어그램 (ALLOW: Contract 박스 연결선, DENY: 점선 + X 마크)
  - Matched Contract / Subject / Filter 상세 테이블
  - 다크모드 대응
- tests/test_api.py: 시뮬레이터 테스트 18개 추가
  - TestSimulatorTenantsAPI (2개), TestSimulatorEpgsAPI (3개), TestSimulatorAPI (13개)
  - 전체 테스트: 58 passed, 1 skipped

### Changed
- backend/main.py: 버전 v1.4.0으로 업데이트, 시뮬레이터 라우터 등록

## [1.3.0] - 2026-03-25
### Added
- Config Linter / Validator 기능 추가
  - GET /api/lint: APIC Live 조회 기반 실시간 분석
  - POST /api/lint/upload: APIC export JSON 파일 업로드 기반 오프라인 분석
- backend/services/linter_engine.py: 규칙 평가 엔진 (DataCollector, RuleEngine, LinterService)
- backend/routers/linter.py: Linter API 엔드포인트
- Linter 규칙 8개 구현
  - SEC-001: permitAll 계열 위험 Contract 탐지
  - SEC-002: Subject 없는 빈 Contract 탐지
  - SEC-003: Filter 없는 빈 Subject 탐지
  - BP-001: BD 미연결 EPG 탐지
  - BP-002: Contract 미연결 고립 EPG 탐지
  - BP-003: Subnet 없는 BD 탐지
  - NM-001: 이름 내 공백/특수문자 탐지
  - NM-002: config.yaml 정의 Prefix 규칙 위반 탐지 (선택 적용)
- config.yaml.example: linter.naming 섹션 추가
- tests/test_api.py: Linter 테스트 21개 추가 (TestLinterAPI 5개, TestLinterUploadAPI 16개)
- frontend/index.html: Config Linter 섹션 UI 추가 (Live Scan / Upload JSON 버튼, 결과 테이블)

### Changed
- frontend/index.html: 시멘틱 HTML 구조 전면 개편
  - div → header, main, footer, section, article 태그 적용
  - aria-label, aria-live, aria-hidden, role 접근성 속성 추가
  - 모달 title h5 → h2.h5 (문서 계층 구조 준수)
- backend/services/aci_client.py: get() 반환 시 class_name 키 없는 항목 필터링
  - APIC 세션 만료/인증 실패 시 error 오브젝트로 인한 KeyError 방지
- main.py: 버전 주석 v1.3.0으로 업데이트

### Fixed
- APIC 로그인 실패 또는 세션 만료 시 /api/all 500 에러 (KeyError: 'faultInst')

## [1.2.1] - 2026-03-25
### Added
- GitHub Actions CI/CD 파이프라인 (.github/workflows/ci.yml)
  - flake8, black, pytest 자동 실행
  - 트리거: main 브랜치 push, 모든 pull_request
- Dockerfile (python:3.12-slim 기반 컨테이너 이미지)
- docker_compose.yml (로컬 개발 환경 오케스트레이션)
- .env.example (Docker 환경변수 템플릿)
- .flake8 (flake8 코드 스타일 설정, max-line-length 120)
- requirements_dev.txt (개발/테스트 의존성 분리)

### Changed
- requirements.txt 버전 고정 (재현 가능한 빌드 환경)
- .gitignore 업데이트 (.env, config.yaml.local, config.yaml.sandbox 추가)

### Fixed
- flake8 E402 (backend/main.py sys.path.append 구조)
- flake8 E501 (tests/test_api.py mock DN 문자열 단축)
- black 포맷 적용 (11개 파일)

## [1.2.0] - 2026-03-24
### Added
- tests/test_api.py: pytest 기반 API 엔드포인트 단위 테스트 (ACIClient Mock 처리)
- tests/conftest.py: pytest 사전 패치 설정 (config.yaml, StaticFiles 없이 실행)

### Changed
- README.md: 대시보드 스크린샷 추가

## [1.1.0] - 2026-02-04
### Added
- 자동 새로고침 기능 (30초)
- Endpoint 검색 API (/api/endpoint/search)
- MAC/IP 검색 UI
- 다크/라이트 테마 전환
- CSV 내보내기
- Fault 상세 모달
- 하단 상태 바 (마지막 업데이트 시간)
- Capacity 섹션 추가

### Changed
- UI 레이아웃 개선
- 토폴로지 시각화 개선

## [1.0.0] - 2026-02-04
### Added
- FastAPI 백엔드 (7개 API)
- Bootstrap 대시보드 UI
- 3가지 테마 (기본, 다크, 기업용)
- Health Check, Policy, Interface, Endpoint, Audit, Capacity, Topology 모듈