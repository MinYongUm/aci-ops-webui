# 설치 가이드

## Ubuntu + Docker (권장)

Docker가 없으면 자동으로 설치합니다.

```bash
curl -fsSL https://raw.githubusercontent.com/MinYongUm/aci-ops-webui/main/install.sh | bash
```

설치 후 디렉토리 구조:
```
~/aci-ops-webui/
├── docker-compose.release.yml
├── config.yaml      # APIC 설정 (Setup UI에서 자동 생성)
├── users.yaml       # 사용자 계정 (자동 생성)
└── .secret_key      # JWT 서명 키 (자동 생성)
```

업데이트 시 동일 명령을 재실행합니다.
기존 APIC 설정(config.yaml)과 사용자 계정(users.yaml)은 자동으로 보존됩니다.

## Docker Hub (수동 설치 — Windows / Mac 포함)

Docker Desktop만 있으면 Git, Python 없이 실행할 수 있습니다.

```bash
# 1. Compose 파일 다운로드
curl -fsSL https://raw.githubusercontent.com/MinYongUm/aci-ops-webui/main/docker-compose.release.yml \
    -o docker-compose.release.yml

# 2. 볼륨 마운트 대상 파일 사전 생성
touch config.yaml users.yaml .secret_key          # Linux/Mac
# New-Item config.yaml, users.yaml, .secret_key -ItemType File  # Windows PowerShell

# 3. 실행
docker compose -f docker-compose.release.yml up -d
```

업데이트:
```bash
docker compose -f docker-compose.release.yml pull
docker compose -f docker-compose.release.yml up -d
```

## 개발 환경 (로컬 실행)

```bash
# 의존성 설치
pip install -r requirements_dev.txt

# 로컬 실행
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Docker 로컬 빌드
docker compose up --build -d
```

Ubuntu 서버 환경 (회사 SSL 프록시 대응):
```bash
pip3 install -r requirements_dev.txt --break-system-packages \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org
```

pytest PATH 미인식 시 (최초 1회):
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

## 운영 명령어

```bash
# 상태 확인
docker compose -f ~/aci-ops-webui/docker-compose.release.yml ps

# 로그 확인
docker compose -f ~/aci-ops-webui/docker-compose.release.yml logs -f

# 재시작
docker compose -f ~/aci-ops-webui/docker-compose.release.yml restart

# 중지
docker compose -f ~/aci-ops-webui/docker-compose.release.yml down
```

## 테스트

```bash
pytest tests/ -v
# 104 passed, 1 skipped (v1.9.5 기준)
```