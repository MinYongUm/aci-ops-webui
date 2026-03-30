![CI](https://github.com/MinYongUm/aci-ops-webui/actions/workflows/ci.yml/badge.svg)

# ACI Ops WebUI

Cisco ACI 운영 자동화 웹 대시보드입니다.
FastAPI 백엔드와 Bootstrap 프론트엔드로 구성되어 있습니다.

## 기능

| 모듈 | 설명 |
|------|------|
| Health Check | Fault 및 노드 상태 확인 |
| Policy Check | 정책 검증 및 보안 감사 |
| Interface Monitor | 인터페이스 상태 모니터링 |
| Endpoint Tracker | Endpoint 위치 추적 |
| Audit Log | 설정 변경 이력 조회 |
| Capacity Report | TCAM 용량 리포트 |
| Topology Viewer | Spine-Leaf 토폴로지 시각화 |
| Config Linter | 설정 검증 및 Best Practice 감사 |
| Microsegmentation Simulator | EPG 간 트래픽 허용/차단 판정 및 시각화 |

## 설치 (Ubuntu + Docker — 권장)

```bash
curl -fsSL https://raw.githubusercontent.com/MinYongUm/aci-ops-webui/main/install.sh | bash
```

설치 완료 후 브라우저에서 접속하면 초기 설정 페이지(`/setup`)로 자동 이동합니다.
APIC 접속 정보를 입력하고 Test Connection → Save를 완료하면 대시보드를 사용할 수 있습니다.

업데이트 시 동일 명령을 재실행합니다. 기존 APIC 설정(config.yaml)은 자동으로 보존됩니다.

## 설치 (수동)

운영 환경 (FastAPI 앱 실행)
```
pip install -r requirements.txt
```

개발 환경 (flake8, black, pytest 포함)
```
pip install -r requirements_dev.txt
```

Ubuntu 서버 환경 (회사 SSL 프록시 대응)
```
pip3 install -r requirements_dev.txt --break-system-packages \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org
```

## 설정

APIC 접속 정보는 설치 후 브라우저의 `/setup` 페이지에서 입력할 수 있습니다.
수동으로 설정하려면 아래와 같이 config.yaml을 직접 작성합니다.

```
cd backend
copy config.yaml.example config.yaml
# config.yaml 편집: hosts, username, password 입력
```

### config.yaml 구조

```yaml
apic:
  hosts:
    - "https://APIC1_IP_OR_HOSTNAME"   # Primary
    - "https://APIC2_IP_OR_HOSTNAME"   # Failover (클러스터 구성 시)
    - "https://APIC3_IP_OR_HOSTNAME"   # Failover (클러스터 구성 시)
  username: "계정명"
  password: "비밀번호"
  timeout: 30   # API 요청 타임아웃 (초)
  retry: 3      # Failover 재시도 횟수
```

APIC 단독(1대) 구성은 `hosts`에 1개만 입력합니다.
Primary 연결 실패 시 다음 host로 자동 전환됩니다.

## 인증

v1.9.2부터 로그인이 필요합니다. 최초 설치 시 기본 계정이 자동 생성됩니다.

| 항목 | 값 |
|------|-----|
| 기본 계정 | admin |
| 기본 비밀번호 | aci-ops-admin |

로그인 후 Settings > Users 메뉴에서 비밀번호 변경 및 추가 계정을 생성할 수 있습니다.

### 역할

| 역할 | 권한 |
|------|------|
| admin | 전체 기능 접근 + 설정 변경 + 사용자 관리 |
| viewer | 모든 대시보드 조회만 가능 (설정 변경 불가) |

## 실행
```
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

브라우저에서 `http://localhost:8000` 접속

## Docker (로컬 개발 환경)
```
# .env 준비
copy .env.example .env

# 컨테이너 실행 (config.yaml은 /setup 페이지에서 설정)
docker compose up --build -d
```

## API 엔드포인트

| Endpoint | 설명 |
|----------|------|
| GET /login | 로그인 페이지 |
| POST /api/auth/login | 로그인 (JWT 발급) |
| POST /api/auth/logout | 로그아웃 |
| GET /api/auth/me | 현재 사용자 조회 |
| GET /api/users | 사용자 목록 (admin) |
| POST /api/users | 사용자 생성 (admin) |
| DELETE /api/users/{username} | 사용자 삭제 (admin) |
| PUT /api/users/{username}/password | 비밀번호 변경 (admin) |
| GET /setup | 초기 설정 페이지 (config.yaml 미존재 시 자동 리다이렉트) |
| POST /api/setup/test | APIC 연결 테스트 |
| POST /api/setup/save | APIC 설정 저장 |
| GET /api/setup/config | 현재 APIC 설정 조회 (password 마스킹) |
| GET /api/health | 헬스 체크 |
| GET /api/policy | 정책 검증 |
| GET /api/interface | 인터페이스 상태 |
| GET /api/endpoint | Endpoint 통계 |
| GET /api/endpoint/search?q= | MAC/IP 검색 |
| GET /api/audit | Audit Log |
| GET /api/capacity | 용량 리포트 |
| GET /api/topology | 토폴로지 |
| GET /api/lint | Config Linter (Live 조회) |
| POST /api/lint/upload | Config Linter (JSON 파일 업로드) |
| GET /api/simulate/tenants | Tenant 목록 조회 (드롭다운용) |
| GET /api/simulate/epgs?tenant= | EPG 목록 조회 (드롭다운용) |
| POST /api/simulate | 트래픽 허용/차단 판정 |
| GET /api/all | 전체 데이터 병렬 조회 |

## Config Linter

ACI 설정의 보안 취약점과 Best Practice 위반을 자동으로 탐지합니다.

| Rule ID | 분류 | 탐지 내용 |
|---------|------|-----------|
| SEC-001 | Security | permitAll 계열 위험 Contract |
| SEC-002 | Security | Subject 없는 빈 Contract |
| SEC-003 | Security | Filter 없는 빈 Subject |
| BP-001 | Best Practice | BD 미연결 EPG |
| BP-002 | Best Practice | Contract 미연결 고립 EPG |
| BP-003 | Best Practice | Subnet 없는 BD |
| NM-001 | Naming | 이름 내 공백/특수문자 |
| NM-002 | Naming | Prefix 규칙 위반 (config.yaml 정의 시) |

Live Scan과 APIC export JSON 파일 업로드 두 가지 방식을 지원합니다.

## Microsegmentation Simulator

EPG 간 트래픽 허용/차단 여부를 ACI Whitelist 모델 기준으로 판정합니다.

**판정 기준**
- Source EPG(Consumer)와 Destination EPG(Provider)가 동일 Contract로 연결되어 있고, 해당 Contract에 Subject + Filter가 존재하면 ALLOW
- 위 조건을 만족하는 Contract가 없으면 ACI 기본 정책(Deny-All) 적용 → DENY

**사용 방법**
1. Source Tenant / EPG 선택
2. Destination Tenant / EPG 선택
3. Simulate 버튼 클릭
4. 판정 결과, 경로 다이어그램, Contract 상세 확인

## 프로젝트 구조
```
aci-ops-webui/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI (Slack 알림 포함)
├── .flake8                      # flake8 설정
├── .env.example                 # 환경변수 템플릿
├── Dockerfile                   # 컨테이너 이미지
├── docker-compose.yml           # 로컬 개발 환경
├── install.sh                   # Ubuntu + Docker 원스텝 설치 스크립트
├── requirements.txt             # 런타임 의존성
├── requirements_dev.txt         # 개발 의존성
├── backend/
│   ├── main.py                  # FastAPI 앱
│   ├── config.yaml              # APIC 설정 (gitignore)
│   ├── config.yaml.example      # APIC 설정 템플릿
│   ├── users.yaml               # 사용자 계정 (gitignore)
│   ├── .secret_key              # JWT 서명 키 (gitignore)
│   ├── services/
│   │   ├── aci_client.py        # ACI API 클라이언트 (Failover, Lock 지원)
│   │   ├── auth_service.py      # JWT 인증, bcrypt 해싱, 사용자 관리
│   │   ├── linter_engine.py     # Config Linter 규칙 엔진
│   │   └── simulator_engine.py  # Microsegmentation Simulator 엔진
│   └── routers/
│       ├── auth.py              # 인증 API (login, logout, me)
│       ├── users.py             # 사용자 관리 API (admin 전용)
│       ├── health.py
│       ├── policy.py
│       ├── interface.py
│       ├── endpoint.py
│       ├── audit.py
│       ├── capacity.py
│       ├── topology.py
│       ├── linter.py            # Config Linter API
│       ├── simulator.py         # Microsegmentation Simulator API
│       └── setup.py             # 초기 설정 API
├── frontend/
│   ├── index.html               # 대시보드 HTML 뼈대 (v1.9.2)
│   ├── login.html               # 로그인 페이지 (v1.9.2)
│   ├── setup.html               # 초기 설정 페이지 (v1.9.0)
│   ├── css/
│   │   └── style.css            # Cisco DevNet 다크 테마
│   └── js/
│       ├── common.js            # STATE, 네비게이션, apiFetch, 유틸리티
│       ├── auth.js              # 사용자 정보 로드, 로그아웃
│       ├── dashboard.js
│       ├── health.js
│       ├── policy.js
│       ├── interface.js
│       ├── endpoint.js
│       ├── audit.js
│       ├── capacity.js
│       ├── topology.js
│       ├── linter.js
│       ├── simulator.js
│       ├── settings.js
│       └── users.js             # 사용자 관리 섹션
└── tests/
    ├── conftest.py              # pytest 패치 설정
    └── test_api.py              # API 단위 테스트 (103 passed, 1 skipped)
```

## 테스트

```
pytest tests/ -v
```

v1.9.2 기준: 103 passed, 1 skipped

Ubuntu 서버에서 pytest PATH 미인식 시:
```
# PATH 추가 (최초 1회)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

pytest tests/ -v
```

## 환경

- Python 3.12.2
- FastAPI
- Cisco ACI APIC

## Screenshots

![ACI Ops Dashboard](https://github.com/user-attachments/assets/6aa82319-4079-43e5-83fe-98b59d7ef88d)