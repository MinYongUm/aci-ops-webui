#!/usr/bin/env bash
# ============================================
# ACI Ops WebUI — install.sh
# 목적: Ubuntu 환경에서 원스텝 설치 및 업데이트
# 버전: v1.9.3
#
# 사용법:
#   curl -fsSL https://raw.githubusercontent.com/MinYongUm/aci-ops-webui/main/install.sh | bash
#   또는
#   bash install.sh
# ============================================

set -euo pipefail

# ============================================
# 상수 정의
# ============================================
REPO_OWNER="MinYongUm"
REPO_NAME="aci-ops-webui"
INSTALL_DIR="${HOME}/${REPO_NAME}"
PORT=8001

# 터미널 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ============================================
# 출력 헬퍼 함수
# ============================================
info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }
step()    { echo -e "\n${BOLD}${CYAN}>>> $*${RESET}"; }
divider() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }

# ============================================
# 시작 배너
# ============================================
clear
divider
echo -e "${BOLD}  ACI Ops WebUI — Installer v1.9.3${RESET}"
echo -e "  https://github.com/${REPO_OWNER}/${REPO_NAME}"
divider
echo ""

# ============================================
# Step 1. 필수 도구 확인 (curl, unzip)
# ============================================
step "Step 1. 필수 도구 확인"

if ! command -v curl &>/dev/null; then
    warn "curl이 없습니다. 설치를 시도합니다..."
    sudo apt-get update -qq && sudo apt-get install -y curl
    success "curl 설치 완료"
else
    success "curl 확인 완료 ($(curl --version | head -1))"
fi

if ! command -v unzip &>/dev/null; then
    warn "unzip이 없습니다. 설치를 시도합니다..."
    sudo apt-get update -qq && sudo apt-get install -y unzip
    success "unzip 설치 완료"
else
    success "unzip 확인 완료"
fi

# ============================================
# Step 2. Docker 설치 확인
# ============================================
step "Step 2. Docker 확인"

if ! command -v docker &>/dev/null; then
    warn "Docker가 설치되어 있지 않습니다."
    echo ""
    echo "  계속 진행하려면 Docker가 필요합니다."
    echo ""
    echo -e "  ${BOLD}[1]${RESET} Docker 자동 설치 후 계속"
    echo -e "  ${BOLD}[2]${RESET} 설치 안내만 출력 후 종료"
    echo ""
    read -rp "  선택 (1 또는 2): " docker_choice

    case "${docker_choice}" in
        1)
            info "Docker 자동 설치를 시작합니다..."
            curl -fsSL https://get.docker.com | sudo sh
            sudo usermod -aG docker "${USER}"
            sudo systemctl enable docker
            success "Docker 설치 완료"
            warn "그룹 변경 적용을 위해 로그아웃 후 재로그인이 필요할 수 있습니다."
            warn "이번 설치는 sudo docker 명령으로 계속 진행합니다."
            DOCKER_CMD="sudo docker"
            COMPOSE_CMD="sudo docker compose"
            ;;
        2)
            echo ""
            info "Docker 설치 방법:"
            echo "  curl -fsSL https://get.docker.com | sudo sh"
            echo "  sudo usermod -aG docker \${USER}"
            echo "  (로그아웃 후 재로그인)"
            echo ""
            info "Docker 설치 완료 후 install.sh를 다시 실행하세요."
            exit 0
            ;;
        *)
            error "잘못된 선택입니다. 종료합니다."
            exit 1
            ;;
    esac
else
    success "Docker 확인 완료 ($(docker --version))"
    sudo systemctl enable docker 2>/dev/null || true
    DOCKER_CMD="docker"

    # Docker Compose v2 확인 (plugin 방식)
    if docker compose version &>/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        warn "Docker Compose를 찾을 수 없습니다. 설치를 시도합니다..."
        sudo apt-get update -qq && sudo apt-get install -y docker-compose-plugin
        COMPOSE_CMD="docker compose"
    fi
    success "Docker Compose 확인 완료 (${COMPOSE_CMD})"
fi

# ============================================
# Step 3. 최신 태그 조회 및 소스 취득
# ============================================
step "Step 3. 최신 버전 확인"

LATEST_TAG=$(curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/tags" \
    | grep '"name"' | head -1 | cut -d'"' -f4)

if [[ -z "${LATEST_TAG}" ]]; then
    error "GitHub에서 최신 태그를 가져올 수 없습니다."
    error "네트워크 연결을 확인하고 다시 시도하세요."
    exit 1
fi

success "최신 버전: ${LATEST_TAG}"

# 이미 설치된 경우 확인
if [[ -d "${INSTALL_DIR}" ]]; then
    info "기존 설치 감지: ${INSTALL_DIR}"

    # 현재 설치된 버전 확인 (CHANGELOG.md에서 첫 번째 버전 태그 추출)
    CURRENT_TAG=""
    if [[ -f "${INSTALL_DIR}/CHANGELOG.md" ]]; then
        CURRENT_TAG=$(grep -m1 '^\## \[' "${INSTALL_DIR}/CHANGELOG.md" \
            | sed 's/## \[/v/' | cut -d']' -f1 || true)
    fi

    if [[ -n "${CURRENT_TAG}" && "${CURRENT_TAG}" == "${LATEST_TAG}" ]]; then
        success "이미 최신 버전(${LATEST_TAG})이 설치되어 있습니다."
        info "서비스 상태를 확인하고 재시작합니다..."
    else
        if [[ -n "${CURRENT_TAG}" ]]; then
            info "업데이트: ${CURRENT_TAG} → ${LATEST_TAG}"
        fi
    fi
else
    info "신규 설치: ${INSTALL_DIR}"
fi

# ============================================
# Step 4. 소스 다운로드 및 배포
# ============================================
step "Step 4. 소스 다운로드 (${LATEST_TAG})"

WORK_DIR=$(mktemp -d)
ZIP_PATH="${WORK_DIR}/${REPO_NAME}-${LATEST_TAG}.zip"

info "다운로드 중: ${LATEST_TAG}.zip"
curl -fsSL \
    "https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/tags/${LATEST_TAG}.zip" \
    -o "${ZIP_PATH}"

success "다운로드 완료"

# 압축 해제
info "압축 해제 중..."
unzip -q "${ZIP_PATH}" -d "${WORK_DIR}"

# 압축 해제된 디렉토리 이름 확인 (태그에 따라 달라질 수 있음)
EXTRACTED=$(find "${WORK_DIR}" -maxdepth 1 -type d -name "${REPO_NAME}*" | head -1)

if [[ -z "${EXTRACTED}" ]]; then
    error "압축 해제 실패: 디렉토리를 찾을 수 없습니다."
    rm -rf "${WORK_DIR}"
    exit 1
fi

# ============================================
# Step 5. 기존 데이터 보존 후 파일 배포
# ============================================
step "Step 5. 파일 배포"

CONFIG_BACKUP=""
USERS_BACKUP=""
SECRET_KEY_BACKUP=""

if [[ -d "${INSTALL_DIR}" ]]; then
    # config.yaml 백업 (APIC 접속 정보)
    if [[ -f "${INSTALL_DIR}/backend/config.yaml" ]]; then
        CONFIG_BACKUP="${WORK_DIR}/config.yaml.backup"
        cp "${INSTALL_DIR}/backend/config.yaml" "${CONFIG_BACKUP}"
        info "기존 config.yaml 백업 완료"
    fi

    # users.yaml 백업 (사용자 계정 정보)
    if [[ -f "${INSTALL_DIR}/backend/users.yaml" ]]; then
        USERS_BACKUP="${WORK_DIR}/users.yaml.backup"
        cp "${INSTALL_DIR}/backend/users.yaml" "${USERS_BACKUP}"
        info "기존 users.yaml 백업 완료"
    fi

    # .secret_key 백업 (JWT 서명 키 — 변경 시 기존 세션 무효화)
    if [[ -f "${INSTALL_DIR}/backend/.secret_key" ]]; then
        SECRET_KEY_BACKUP="${WORK_DIR}/secret_key.backup"
        cp "${INSTALL_DIR}/backend/.secret_key" "${SECRET_KEY_BACKUP}"
        info "기존 .secret_key 백업 완료"
    fi

    # 기존 설치 디렉토리 제거 후 재배포
    rm -rf "${INSTALL_DIR}"
fi

# 새 버전 배포
mv "${EXTRACTED}" "${INSTALL_DIR}"
success "파일 배포 완료: ${INSTALL_DIR}"

# config.yaml 복원
if [[ -n "${CONFIG_BACKUP}" && -f "${CONFIG_BACKUP}" ]]; then
    cp "${CONFIG_BACKUP}" "${INSTALL_DIR}/backend/config.yaml"
    success "기존 config.yaml 복원 완료 (APIC 설정 유지됨)"
else
    info "config.yaml 없음 — 서버 기동 후 브라우저에서 초기 설정을 진행하세요."
fi

# users.yaml 복원
if [[ -n "${USERS_BACKUP}" && -f "${USERS_BACKUP}" ]]; then
    cp "${USERS_BACKUP}" "${INSTALL_DIR}/backend/users.yaml"
    success "기존 users.yaml 복원 완료 (사용자 계정 유지됨)"
else
    info "users.yaml 없음 — 최초 실행 시 기본 계정(admin)이 자동 생성됩니다."
fi

# .secret_key 복원
if [[ -n "${SECRET_KEY_BACKUP}" && -f "${SECRET_KEY_BACKUP}" ]]; then
    cp "${SECRET_KEY_BACKUP}" "${INSTALL_DIR}/backend/.secret_key"
    success "기존 .secret_key 복원 완료 (기존 세션 유지됨)"
else
    info ".secret_key 없음 — 최초 실행 시 자동 생성됩니다."
fi

# .env 생성 (.env.example 복사, 없으면 빈 파일 생성)
if [[ ! -f "${INSTALL_DIR}/.env" ]]; then
    if [[ -f "${INSTALL_DIR}/.env.example" ]]; then
        cp "${INSTALL_DIR}/.env.example" "${INSTALL_DIR}/.env"
        success ".env 생성 완료 (.env.example 복사)"
    else
        touch "${INSTALL_DIR}/.env"
        success ".env 생성 완료 (빈 파일)"
    fi
else
    info ".env 이미 존재 — 유지합니다."
fi

# 임시 디렉토리 정리
rm -rf "${WORK_DIR}"

# ============================================
# Step 6. docker compose 실행
# ============================================
step "Step 6. 서비스 시작"

cd "${INSTALL_DIR}"

# Docker 볼륨 마운트 대상 파일 사전 생성
# 파일이 없으면 Docker가 디렉토리로 자동 생성하는 문제 방지
if [[ ! -f "backend/config.yaml" ]]; then
    touch "backend/config.yaml"
    info "config.yaml 빈 파일 생성 완료 (/setup 페이지에서 설정 예정)"
fi

if [[ ! -f "backend/users.yaml" ]]; then
    touch "backend/users.yaml"
    info "users.yaml 빈 파일 생성 완료 (최초 실행 시 기본 계정 자동 생성)"
fi

if [[ ! -f "backend/.secret_key" ]]; then
    touch "backend/.secret_key"
    info ".secret_key 빈 파일 생성 완료 (최초 실행 시 자동 생성)"
fi

# 기존 컨테이너 중지 (있는 경우)
if ${COMPOSE_CMD} ps -q 2>/dev/null | grep -q .; then
    info "기존 컨테이너를 중지합니다..."
    ${COMPOSE_CMD} down
fi

info "컨테이너 빌드 및 시작 중..."
${COMPOSE_CMD} up --build -d

success "서비스 시작 완료"

# ============================================
# 완료 메시지
# ============================================
echo ""
divider
echo -e "${BOLD}${GREEN}  설치 완료!${RESET}"
divider
echo ""

CONFIG_SIZE=$(stat -c%s "${INSTALL_DIR}/backend/config.yaml" 2>/dev/null || echo 0)
if [[ "${CONFIG_SIZE}" -gt 0 ]]; then
    echo -e "  브라우저에서 접속하세요:"
    echo -e "  ${BOLD}${CYAN}http://$(hostname -I | awk '{print $1}'):${PORT}${RESET}"
else
    echo -e "  브라우저에서 초기 설정을 완료하세요:"
    echo -e "  ${BOLD}${CYAN}http://$(hostname -I | awk '{print $1}'):${PORT}/setup${RESET}"
    echo ""
    echo -e "  APIC 접속 정보를 입력하면 대시보드를 사용할 수 있습니다."
fi

echo ""
echo -e "  설치 경로: ${INSTALL_DIR}"
echo -e "  버전:      ${LATEST_TAG}"
echo ""
divider
echo ""