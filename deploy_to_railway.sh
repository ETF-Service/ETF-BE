#!/bin/bash

# ETF Backend Railway 배포 스크립트
# 사용법: ./deploy_to_railway.sh

set -e  # 오류 발생 시 스크립트 중단

echo "🚀 ETF Backend Railway 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Railway CLI 설치 확인
check_railway_cli() {
    log_info "Railway CLI 설치 확인 중..."
    if ! command -v railway &> /dev/null; then
        log_error "Railway CLI가 설치되지 않았습니다."
        echo "다음 명령어로 설치하세요:"
        echo "npm install -g @railway/cli"
        exit 1
    fi
    log_success "Railway CLI 확인 완료"
}

# Railway 로그인 확인
check_railway_login() {
    log_info "Railway 로그인 상태 확인 중..."
    if ! railway whoami &> /dev/null; then
        log_warning "Railway에 로그인되지 않았습니다."
        echo "다음 명령어로 로그인하세요:"
        echo "railway login"
        exit 1
    fi
    log_success "Railway 로그인 확인 완료"
}

# 프로젝트 초기화 확인
check_project_init() {
    log_info "Railway 프로젝트 초기화 확인 중..."
    if [ ! -f ".railway" ]; then
        log_warning "Railway 프로젝트가 초기화되지 않았습니다."
        echo "다음 명령어로 초기화하세요:"
        echo "railway init"
        exit 1
    fi
    log_success "Railway 프로젝트 초기화 확인 완료"
}

# Docker 빌드 테스트
test_docker_build() {
    log_info "Docker 빌드 테스트 중..."
    if docker build -t etf-backend-test . &> /dev/null; then
        log_success "Docker 빌드 테스트 성공"
        docker rmi etf-backend-test &> /dev/null
    else
        log_error "Docker 빌드 테스트 실패"
        exit 1
    fi
}

# 환경변수 확인
check_environment_variables() {
    log_info "환경변수 확인 중..."
    
    # 필수 환경변수 목록
    required_vars=("DATABASE_URL" "PORT")
    optional_vars=("SECRET_KEY" "ALGORITHM" "ACCESS_TOKEN_EXPIRE_MINUTES" "OPENAI_API_KEY")
    
    log_info "필수 환경변수:"
    for var in "${required_vars[@]}"; do
        if railway variables get "$var" &> /dev/null; then
            log_success "  $var: 설정됨"
        else
            log_warning "  $var: 설정되지 않음 (Railway에서 자동 설정됨)"
        fi
    done
    
    log_info "선택적 환경변수:"
    for var in "${optional_vars[@]}"; do
        if railway variables get "$var" &> /dev/null; then
            log_success "  $var: 설정됨"
        else
            log_warning "  $var: 설정되지 않음"
        fi
    done
}

# 배포 실행
deploy_to_railway() {
    log_info "Railway에 배포 중..."
    
    # 현재 Git 상태 확인
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "커밋되지 않은 변경사항이 있습니다."
        read -p "계속 진행하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "배포가 취소되었습니다."
            exit 0
        fi
    fi
    
    # Railway 배포
    if railway up; then
        log_success "배포 성공!"
    else
        log_error "배포 실패"
        exit 1
    fi
}

# 배포 후 확인
verify_deployment() {
    log_info "배포 확인 중..."
    
    # 배포 URL 가져오기
    DEPLOY_URL=$(railway status --json | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$DEPLOY_URL" ]; then
        log_warning "배포 URL을 가져올 수 없습니다."
        return
    fi
    
    log_info "배포 URL: $DEPLOY_URL"
    
    # 헬스체크
    log_info "헬스체크 실행 중..."
    if curl -f -s "$DEPLOY_URL/health" > /dev/null; then
        log_success "헬스체크 성공"
    else
        log_warning "헬스체크 실패 (서비스가 아직 시작되지 않았을 수 있습니다)"
    fi
    
    # 로그 확인
    log_info "최근 로그 확인 중..."
    railway logs --tail 10
}

# 메인 실행
main() {
    echo "=========================================="
    echo "  ETF Backend Railway 배포 스크립트"
    echo "=========================================="
    echo
    
    # 사전 검사
    check_railway_cli
    check_railway_login
    check_project_init
    test_docker_build
    check_environment_variables
    
    echo
    log_info "모든 사전 검사가 완료되었습니다."
    echo
    
    # 배포 실행
    deploy_to_railway
    
    echo
    log_success "배포가 완료되었습니다!"
    echo
    
    # 배포 확인
    verify_deployment
    
    echo
    echo "=========================================="
    log_success "배포 프로세스 완료!"
    echo "=========================================="
}

# 스크립트 실행
main "$@" 