# Changelog

## [1.9.2] - 2026-03-30
### Added
- 인증 시스템 (JWT + httponly 쿠키)
  - POST /api/auth/login: 로그인 (JWT 발급)
  - POST /api/auth/logout: 로그아웃 (쿠키 삭제)
  - GET /api/auth/me: 현재 사용자 조회
- 역할 기반 접근 제어 (admin / viewer)
  - admin: 전체 기능 접근 + 설정 변경 + 사용자 관리
  - viewer: 모든 대시보드 조회만 가능
- 사용자 관리 API (admin 전용)
  - GET /api/users: 사용자 목록 조회
  - POST /api/users: 사용자 생성
  - DELETE /api/users/{username}: 사용자 삭제
  - PUT /api/users/{username}/password: 비밀번호 변경
- backend/services/auth_service.py: JWT 생성/검증, bcrypt 해싱, users.yaml CRUD
- backend/routers/auth.py: 인증 API 엔드포인트
- backend/routers/users.py: 사용자 관리 API 엔드포인트 (admin 전용)
- frontend/login.html: Cisco DevNet 다크 테마 로그인 페이지
- frontend/js/auth.js: 현재 사용자 로드, 로그아웃 처리
- frontend/js/users.js: User Management 섹션 UI
- 사이드바 System 그룹에 Users nav-item 추가 (admin-only)
- 사이드바 하단 로그인 사용자 정보 + 역할 배지 + 로그아웃 버튼 추가
- 기본 admin 계정 자동 생성 (최초 실행 시): admin / aci-ops-admin
- tests/test_api.py: 인증/사용자 관리 테스트 22개 추가 (103 passed, 1 skipped)

### Changed
- main.py: AuthMiddleware 추가 (미인증 요청 → /login 리다이렉트 또는 401)
- main.py: 버전 v1.9.1 → v1.9.2
- common.js: apiFetch 401 응답 시 /login 자동 리다이렉트
- common.js: Users 섹션 추가 (SECTION_META, loadSection, startAutoRefresh 제외)
- index.html: v1.9.2, Users nav-item, Settings/Users admin-only 클래스, 사용자 정보 영역
- requirements.txt: pyjwt==2.10.1, passlib[bcrypt]==1.7.4, bcrypt==4.0.1 추가
- .gitignore: users.yaml, .secret_key 추가

### Fixed
- bcrypt==4.0.1 버전 고정 (passlib 1.7.4와 bcrypt 4.1+ 호환성 문제)

## [1.9.1] - 2026-03-27
### Added
- GET /api/setup/config: 현재 APIC 설정 조회 API (password 마스킹)
- frontend/js/settings.js: Settings 섹션 신규 (APIC Hosts/Username/Password 수정 + Test Connection)
- 사이드바 System 그룹 + Settings nav-item 추가
- 섹션 헤더 우측 상단 설정 아이콘 버튼 추가
- tests/test_api.py: TestSetupConfigAPI (7개 테스트 추가)

### Fixed
- install.sh: config.yaml 빈 파일일 때 /setup 대신 / 로 안내하는 버그 수정 (stat -c%s)

### Changed
- install.sh: Docker 자동시작 설정 추가 (sudo systemctl enable docker)
- common.js: Settings 섹션 자동 새로고침 제외
- 버전 표기 v1.9.0 → v1.9.1

## [1.9.0] - 2026-03-27
### Added
- 초기 설정 UI (`/setup` 페이지) — config.yaml 미존재 시 자동 리다이렉트
- POST /api/setup/test — APIC 연결 테스트 API (config.yaml 저장 없음)
- POST /api/setup/save — APIC 연결 테스트 후 config.yaml 저장 및 ACIClient 재초기화
- SetupRedirectMiddleware — config.yaml 없을 때 `/setup` 이외 모든 요청 차단
- `install.sh` — Ubuntu + Docker 환경 원스텝 설치/업데이트 스크립트
  - GitHub API로 최신 태그 조회 후 zip 다운로드
  - Docker 미설치 시 자동 설치 또는 안내 선택
  - 업데이트 시 기존 config.yaml 자동 보존
- 테스트 13개 추가 (74 passed, 1 skipped)

### Fixed
- ACIClient 지연 초기화 — config.yaml 없어도 서버 정상 기동
- CI 환경 `os.path.exists` 패치 추가 (client fixture)
- Simulator 라우터 항상 등록 (aci None 여부 무관)

## [1.8.0] - 2026-03-27

### Added
- 섹션 헤더 추가 (타이틀 + 부제목 + Refresh 버튼 + Auto 30s 토글)
- 사이드바 브랜드 영역 재설계 (아이콘 박스 + v1.8.0 배지 + "Cisco ACI Operations" 태그라인)
- 사이드바 푸터 추가 (Connected 상태 dot + 마지막 업데이트 시각)

### Changed
- UI 리뉴얼: Cisco DevNet 다크 테마 전면 적용
  - CSS 변수 기반 팔레트 (`--bg-body: #0d1421`, `--cisco-blue: #049fd4` 등)
  - 카드 hover glow 효과 (`box-shadow` + `translateY(-1px)`)
  - 스크롤바 스타일링 (WebKit + Firefox)
  - 사이드바 active 강화 (좌측 3px 바 + 우측 glow dot)
- nav-item 구조 변경 (`.nav-icon` / `.nav-label` / `.nav-badge` 3개 요소 명시적 분리, 아이콘 교체)
- 모든 모듈 JS scaffold inject 방식으로 전환
  - `section-body` 단일 컨테이너 구조 대응
  - 각 `load{Module}()` 진입 시 `_build{Module}Scaffold()`로 HTML 먼저 inject 후 데이터 채움

### Fixed
- `currentSection = 'dashboard'` 초기값으로 인한 `/api/all` 중복 호출 버그 수정
  - 원인: 페이지 로드 시 `navigateTo('dashboard')` 호출 → `section === currentSection` 조건 true
    → `refreshCurrent()` 경로 진입 → `loadDashboard()` 중복 실행
  - 수정: `currentSection = null` 초기화 → 첫 진입 시 정상 경로만 실행

### Test
- 61 passed, 1 skipped (변동 없음 — 백엔드 변경 없음)

## [1.7.0] - 2026-03-27

### Added
- 프론트엔드 CSS/JS 파일 분리
  - `frontend/css/style.css` — 전체 CSS 추출
  - `frontend/js/common.js` — STATE, 네비게이션, apiFetch, 공통 유틸리티
  - `frontend/js/dashboard.js` — Dashboard 섹션
  - `frontend/js/health.js` — Health Check 섹션
  - `frontend/js/policy.js` — Policy Check 섹션
  - `frontend/js/interface.js` — Interface Monitor 섹션
  - `frontend/js/endpoint.js` — Endpoint Tracker 섹션
  - `frontend/js/audit.js` — Audit Log 섹션
  - `frontend/js/capacity.js` — Capacity Report 섹션
  - `frontend/js/topology.js` — Topology Viewer 섹션
  - `frontend/js/linter.js` — Config Linter 섹션
  - `frontend/js/simulator.js` — Microseg Simulator 섹션

### Fixed
- `ACIClient.login()` Race Condition 수정 (`threading.Lock` 적용)
  - `/api/all` 병렬 호출 시 세션 만료(401)를 여러 스레드가 동시에 감지하면
    `login()`이 중복 실행되어 데이터가 빈 배열로 반환되는 문제 해결
  - Double-Checked Locking 패턴으로 불필요한 재로그인 방지

### Changed
- `frontend/index.html` — HTML 뼈대만 유지 (버전 표기 v1.7.0)
- `frontend/legacy/` 폴더 제거 (Git 히스토리로 버전 관리)

### Test
- 61 passed, 1 skipped (v1.6.0과 동일)

## [1.6.0] - 2026-03-26

### Added
- 사이드바 네비게이션 SPA (단일 index.html)
- Dashboard 기본 진입점 (6개 Stat Card + Module Status Grid + Recent Changes)
- 모듈별 독립 섹션 및 전용 API 호출
- 사이드바 배지 (Health Critical+Major / Policy Risk / Capacity High TCAM)
- 툴팁 4개 (Health / Config Linter / Microseg Simulator / Capacity)
- Auto-refresh 현재 섹션만 30초 갱신 (Linter 제외)
- Dockerfile `--trusted-host` 옵션 추가 (회사 SSL 프록시 대응)

### Changed
- 라이트 테마 단일 고정 (다크모드 제거)
- 전체 폰트 사이즈 상향 (body 15px 기준)

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
- tests/test_api.py: 시뮬레이터 테스트 18개 추가
  - TestSimulatorTenantsAPI (2개), TestSimulatorEpgsAPI (3개), TestSimulatorAPI (13개)

### Changed
- backend/main.py: 버전 v1.4.0으로 업데이트, 시뮬레이터 라우터 등록

### Test
- 58 passed, 1 skipped (v1.3.0 대비 +18)

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

### Fixed
- APIC 로그인 실패 또는 세션 만료 시 /api/all 500 에러 (KeyError: 'faultInst')

### Test
- 41 passed, 1 skipped (v1.2.1 대비 +21)

## [1.2.1] - 2026-03-25

### Added
- GitHub Actions CI/CD 파이프라인 (.github/workflows/ci.yml)
  - flake8, black, pytest 자동 실행
  - 트리거: main 브랜치 push, 모든 pull_request
- Dockerfile (python:3.12-slim 기반 컨테이너 이미지)
- docker-compose.yml (로컬 개발 환경 오케스트레이션)
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