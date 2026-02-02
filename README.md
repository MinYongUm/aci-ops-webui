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
```
pip install -r requirements.txt
```

## 실행
```
cd backend
uvicorn main:app --reload --host 127.0.0.0 --port 8000
```

브라우저에서 `http://localhost:8000` 접속

## API 엔드포인트

| Endpoint | 설명 |
|----------|------|
| GET /api/health | 헬스 체크 |
| GET /api/policy | 정책 검증 |
| GET /api/interface | 인터페이스 상태 |
| GET /api/endpoint | Endpoint 통계 |
| GET /api/audit | Audit Log |
| GET /api/capacity | 용량 리포트 |
| GET /api/topology | 토폴로지 |
| GET /api/all | 전체 데이터 |

## 프로젝트 구조
```
aci-ops-webui/
├── backend/
│   ├── main.py              # FastAPI 앱
│   ├── config.yaml          # APIC 설정
│   ├── services/
│   │   └── aci_client.py    # ACI API 클라이언트
│   └── routers/
│       ├── health.py
│       ├── policy.py
│       ├── interface.py
│       ├── endpoint.py
│       ├── audit.py
│       ├── capacity.py
│       └── topology.py
├── frontend/
│   └── index.html           # 대시보드 UI
├── requirements.txt
└── README.md
```

## 환경

- Python 3.12.2
- FastAPI
- Cisco ACI APIC