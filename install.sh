#!/usr/bin/env bash
# ============================================
# ACI Ops WebUI — install.sh
# 목적: Ubuntu 환경에서 원스텝 설치 및 업데이트
# 버전: v1.9.5
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
IMAGE="eomminyong/aci-ops-webui:latest"
COMPOSE_FILE="docker-compose.release.yml"
COMPOSE_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/${COMPOSE_FILE}"
INSTALL_DIR="${HOME}/${REPO_NAME}"
PORT=8001

# 볼륨 마운트 대상 파일 (docker-compose.release.yml 기준 — 설치 디렉토리 루트)
DATA_FILES=("config.yaml" "users.yaml" ".secret_key")

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
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }
step()    { echo -e "\n${BOLD}${CYAN}>>> $*${RESET}"; }
divider() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }

# ============================================
# 시작 배너
# ============================================
clear
divider
echo -e "${BOLD}  ACI Ops WebUI — Installer v1.9.5${RESET}"
echo -e "  https://github.com/${REPO_OWNER}/${REPO_NAME}"
divider
echo ""

# ============================================
# Step 1. 필수 도구 확인 (curl)
# ============================================
step "Step 1. 필수 도구 확인"

if ! command -v curl &>/dev/null; then
    warn "curl이 없습니다. 설치를 시도합니다..."
    sudo apt-get update -qq && sudo apt-get install -y curl
    success "curl 설치 완료"
else
    success "curl 확인 완료 ($(curl --version | head -1))"
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
# Step 3. 기존 설치 감지
# ============================================
step "Step 3. 기존 설치 확인"

IS_UPDATE=false
if [[ -d "${INSTALL_DIR}" && -f "${INSTALL_DIR}/${COMPOSE_FILE}" ]]; then
    IS_UPDATE=true
    warn "기존 설치 감지: 업데이트 모드로 진행합니다."
else
    info "신규 설치로 진행합니다."
fi

# ============================================
# Step 4. [업데이트] 기존 컨테이너 중지 + 데이터 백업
# ============================================
step "Step 4. 데이터 보존 처리"

BACKUP_DIR=""

if [[ "${IS_UPDATE}" == true ]]; then
    cd "${INSTALL_DIR}"

    # 기존 컨테이너 중지
    info "기존 컨테이너를 중지합니다..."
    ${COMPOSE_CMD} -f "${COMPOSE_FILE}" down \
        || warn "컨테이너 중지 실패 (이미 중지된 상태일 수 있습니다)"
    success "컨테이너 중지 완료"

    # 데이터 파일 백업
    BACKUP_DIR=$(mktemp -d)
    for f in "${DATA_FILES[@]}"; do
        SRC="${INSTALL_DIR}/${f}"
        if [[ -f "${SRC}" && -s "${SRC}" ]]; then
            cp "${SRC}" "${BACKUP_DIR}/${f}"
            success "백업: ${f}"
        fi
    done
else
    info "신규 설치 — 건너뜀"
fi

# ============================================
# Step 5. 작업 디렉토리 준비
# ============================================
step "Step 5. 작업 디렉토리 준비"

mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"
success "디렉토리 준비 완료: ${INSTALL_DIR}"

# ============================================
# Step 6. docker-compose.release.yml 다운로드
# ============================================
step "Step 6. Compose 파일 다운로드"

info "다운로드 중: ${COMPOSE_FILE}"
curl -fsSL "${COMPOSE_URL}" -o "${COMPOSE_FILE}" \
    || error "Compose 파일 다운로드 실패: ${COMPOSE_URL}"
success "Compose 파일 다운로드 완료"

# ============================================
# Step 7. 볼륨 마운트 대상 빈 파일 사전 생성
#         파일이 없으면 Docker가 디렉토리로 자동 생성 → IsADirectoryError 발생
# ============================================
step "Step 7. 볼륨 마운트 파일 초기화"

for f in "${DATA_FILES[@]}"; do
    if [[ ! -f "${INSTALL_DIR}/${f}" ]]; then
        touch "${INSTALL_DIR}/${f}"
        info "생성: ${f}"
    else
        info "유지: ${f} (이미 존재)"
    fi
done
success "볼륨 마운트 파일 초기화 완료"

# ============================================
# Step 8. [업데이트] 백업 데이터 복원
# ============================================
step "Step 8. 데이터 복원"

if [[ "${IS_UPDATE}" == true && -n "${BACKUP_DIR}" ]]; then
    for f in "${DATA_FILES[@]}"; do
        BACKUP_FILE="${BACKUP_DIR}/${f}"
        if [[ -f "${BACKUP_FILE}" ]]; then
            cp "${BACKUP_FILE}" "${INSTALL_DIR}/${f}"
            success "복원: ${f}"
        fi
    done
    rm -rf "${BACKUP_DIR}"
else
    info "신규 설치 — 건너뜀"
    info "config.yaml: 서버 기동 후 브라우저에서 초기 설정을 진행하세요."
    info "users.yaml: 최초 실행 시 기본 계정(admin)이 자동 생성됩니다."
    info ".secret_key: 최초 실행 시 자동 생성됩니다."
fi

# ============================================
# Step 9. Docker Hub에서 최신 이미지 pull
# ============================================
step "Step 9. 최신 이미지 pull"

info "이미지: ${IMAGE}"
${DOCKER_CMD} pull "${IMAGE}" \
    || error "이미지 pull 실패. 네트워크 연결과 Docker Hub 상태를 확인하세요."
success "이미지 pull 완료"

# ============================================
# Step 10. 컨테이너 시작
# ============================================
step "Step 10. 서비스 시작"

${COMPOSE_CMD} -f "${COMPOSE_FILE}" up -d \
    || error "컨테이너 시작 실패"
success "서비스 시작 완료"

# ============================================
# 완료 메시지
# ============================================
CONFIG_SIZE=$(stat -c%s "${INSTALL_DIR}/config.yaml" 2>/dev/null || echo 0)
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
divider
echo -e "${BOLD}${GREEN}  설치 완료!${RESET}"
divider
echo ""

if [[ "${CONFIG_SIZE}" -gt 0 ]]; then
    # 업데이트: 기존 config.yaml 유지 — 바로 접속 가능
    echo -e "  브라우저에서 접속하세요:"
    echo -e "  ${BOLD}${CYAN}http://localhost:${PORT}${RESET}"
    echo -e "  (원격 접근: http://${SERVER_IP}:${PORT})"
else
    # 신규 설치: 로그인 후 APIC 설정 필요
    echo -e "  브라우저에서 접속 후 초기 설정을 완료하세요:"
    echo -e "  ${BOLD}${CYAN}http://localhost:${PORT}${RESET}"
    echo -e "  (원격 접근: http://${SERVER_IP}:${PORT})"
    echo ""
    echo -e "  접속 순서:"
    echo -e "    1) 로그인 (아래 기본 계정 사용)"
    echo -e "    2) APIC 접속 정보 입력 (Setup 페이지)"
    echo -e "    3) 대시보드 사용"
    echo ""
    echo -e "  기본 계정:"
    echo -e "    username: ${BOLD}admin${RESET}"
    echo -e "    password: ${BOLD}aci-ops-admin${RESET}"
    echo -e "    ${YELLOW}(최초 로그인 후 반드시 비밀번호를 변경하세요)${RESET}"
fi

echo ""
echo -e "  설치 경로: ${INSTALL_DIR}"
echo -e "  이미지:    ${IMAGE}"
echo ""
divider
echo -e "${BOLD}  운영 명령어${RESET}"
divider
echo -e "  상태 확인:  ${COMPOSE_CMD} -f ${INSTALL_DIR}/${COMPOSE_FILE} ps"
echo -e "  로그 확인:  ${COMPOSE_CMD} -f ${INSTALL_DIR}/${COMPOSE_FILE} logs -f"
echo -e "  재시작:     ${COMPOSE_CMD} -f ${INSTALL_DIR}/${COMPOSE_FILE} restart"
echo -e "  중지:       ${COMPOSE_CMD} -f ${INSTALL_DIR}/${COMPOSE_FILE} down"
echo -e "  업데이트:   curl -fsSL https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/install.sh | bash"
echo ""
divider
echo ""