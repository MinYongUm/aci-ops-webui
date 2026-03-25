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

## 설치

운영 환경 (FastAPI 앱 실행)
```
pip install -r requirements.txt
```

개발 환경 (flake8, black, pytest 포함)
```
pip install -r requirements_dev.txt
```

## 실행
```
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

브라우저에서 `http://localhost:8000` 접속

## Docker (로컬 개발 환경)
```
# .env.example 복사 후 수정
copy .env.example .env

# 컨테이너 실행
docker compose up
```

## API 엔드포인트

| Endpoint | 설명 |
|----------|------|
| GET /api/health | 헬스 체크 |
| GET /api/policy | 정책 검증 |
| GET /api/interface | 인터페이스 상태 |
| GET /api/endpoint | Endpoint 통계 |
| GET /api/endpoint/search?q= | MAC/IP 검색 |
| GET /api/audit | Audit Log |
| GET /api/capacity | 용량 리포트 |
| GET /api/topology | 토폴로지 |
| GET /api/all | 전체 데이터 |

## 프로젝트 구조
```
aci-ops-webui/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI
├── .flake8                      # flake8 설정
├── .env.example                 # 환경변수 템플릿
├── Dockerfile                   # 컨테이너 이미지
├── docker_compose.yml           # 로컬 개발 환경
├── requirements.txt             # 런타임 의존성
├── requirements_dev.txt         # 개발 의존성
├── backend/
│   ├── main.py                  # FastAPI 앱
│   ├── config.yaml              # APIC 설정 (gitignore)
│   ├── config.yaml.example      # APIC 설정 템플릿
│   ├── services/
│   │   └── aci_client.py        # ACI API 클라이언트
│   └── routers/
│       ├── health.py
│       ├── policy.py
│       ├── interface.py
│       ├── endpoint.py
│       ├── audit.py
│       ├── capacity.py
│       └── topology.py
├── frontend/
│   └── index.html               # 대시보드 UI
└── tests/
    ├── conftest.py              # pytest 패치 설정
    └── test_api.py              # API 단위 테스트
```

## 환경

- Python 3.12.2
- FastAPI
- Cisco ACI APIC

## Screenshots

![ACI Ops Dashboard](https://github.com/user-attachments/assets/6aa82319-4079-43e5-83fe-98b59d7ef88d)