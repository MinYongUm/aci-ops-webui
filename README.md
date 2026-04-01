![CI](https://github.com/MinYongUm/aci-ops-webui/actions/workflows/ci.yml/badge.svg)
![Docker Hub](https://img.shields.io/docker/v/eomminyong/aci-ops-webui?label=Docker%20Hub)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)

# ACI Ops WebUI

Cisco ACI 운영 자동화 웹 대시보드


## Why ACI Ops WebUI?

Cisco APIC 기본 UI는 운영에 필요한 정보를 찾으려면 여러 메뉴를 돌아다녀야 합니다.

이 도구는 Fault 조회, Endpoint 추적, 정책 검증 등 운영 빈도가 높은 기능을 한 화면에 통합하여 현장 엔지니어의 운영 효율을 높이기 위해 개발했습니다.


## Screenshots

![ACI Ops Dashboard](https://github.com/user-attachments/assets/6aa82319-4079-43e5-83fe-98b59d7ef88d)


## 기능

| 모듈 | 설명 |
|------|------|
| Health Check | Fault 심각도별 집계 및 노드 상태 확인 |
| Policy Check | Contract 보안 위험 탐지 |
| Interface Monitor | 인터페이스 Up/Down 및 Down 원인 분류 |
| Endpoint Tracker | MAC/IP 기반 Endpoint 위치 추적 |
| Audit Log | 설정 변경 이력 및 사용자별 통계 |
| Capacity Report | TCAM 사용률 리포트 및 고사용 노드 감지 |
| Topology Viewer | Spine-Leaf 토폴로지 시각화 |
| Config Linter | 설정 검증 및 Best Practice 위반 탐지 |
| Microsegmentation Simulator | EPG 간 트래픽 허용/차단 판정 |


## 기술 스택

| 영역 | 사용 기술 |
|------|-----------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Frontend | Bootstrap 5, Vanilla JS |
| 인증 | JWT (httponly 쿠키), bcrypt |
| 배포 | Docker, Docker Compose, GitHub Actions |
| 테스트 | pytest (104 passed), unittest.mock |
| CI/CD | GitHub Actions → Docker Hub 자동 push |


## 빠른 시작

```bash
curl -fsSL https://raw.githubusercontent.com/MinYongUm/aci-ops-webui/main/install.sh | bash
```

Ubuntu 서버에서 한 줄로 설치합니다. Docker가 없으면 자동으로 설치합니다.

설치 완료 후: 브라우저에서 서버 IP 접속 → 로그인 → APIC 설정 → 대시보드 사용


## 문서

- [설치 가이드](INSTALL.md) — install.sh, Docker Hub 수동 설치, 운영 명령어
- [설정 가이드](CONFIGURATION.md) — APIC 연결, Config Linter 규칙, 인증 및 역할
- [개발 가이드](CONTRIBUTING.md) — 로컬 실행, 테스트, 기여 방법