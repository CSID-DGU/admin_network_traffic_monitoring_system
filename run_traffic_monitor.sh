#!/bin/bash

# ===== Traffic Monitor Runner Script =====
# Git pull and run traffic monitor with user configuration
# Usage: ./run_traffic_monitor.sh

# 설정 파일 로드
SCRIPT_DIR="$(dirname "$0")"
CONFIG_FILE="$SCRIPT_DIR/config.sh"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "ERROR: 설정 파일이 없습니다: $CONFIG_FILE"
    echo "config.sh.example 파일을 config.sh로 복사한 후 설정을 수정하세요."
    echo "cp config.sh.example config.sh"
    exit 1
fi

source "$CONFIG_FILE"

# 스크립트 경로 설정
PYTHON_SCRIPT="$SCRIPT_DIR/traffic_monitor.py"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/traffic_monitor.log"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

# 로그 함수
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 에러 처리 함수
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 설정 검증
validate_config() {
    if [[ "$SERVER_NAME" == "your-server-name" ]]; then
        error_exit "SERVER_NAME이 설정되지 않았습니다. 스크립트 상단에서 설정하세요."
    fi
    
    if [[ "$SERVER_IP" == "your-server-ip" ]]; then
        error_exit "SERVER_IP가 설정되지 않았습니다. 스크립트 상단에서 설정하세요."
    fi
    
    if [[ "$INTERFACE" == "your-interface" ]]; then
        error_exit "INTERFACE가 설정되지 않았습니다. 스크립트 상단에서 설정하세요."
    fi
    
    if [[ "$APPS_SCRIPT_URL" == "your-apps-script-url" ]]; then
        error_exit "APPS_SCRIPT_URL이 설정되지 않았습니다. 스크립트 상단에서 설정하세요."
    fi
    
}

# Git 저장소 업데이트
update_repository() {
    log "Git 저장소 업데이트 중..."
    
    cd "$SCRIPT_DIR" || error_exit "디렉토리 이동 실패: $SCRIPT_DIR"
    
    # Git pull 실행
    if git pull origin main > /tmp/git_pull.log 2>&1; then
        log "Git pull 성공"
        if grep -q "Already up to date" /tmp/git_pull.log; then
            log "이미 최신 버전입니다"
        else
            log "새로운 업데이트가 적용되었습니다"
        fi
    else
        log "WARNING: Git pull 실패, 기존 버전으로 계속 진행"
        cat /tmp/git_pull.log >> "$LOG_FILE"
    fi
    
    rm -f /tmp/git_pull.log
}

# Python 스크립트 실행
run_monitor() {
    log "트래픽 모니터 실행 중..."
    log "서버 정보: $SERVER_NAME ($SERVER_IP) - $INTERFACE"
    log "Apps Script URL: $APPS_SCRIPT_URL"
    
    cd "$SCRIPT_DIR" || error_exit "디렉토리 이동 실패: $SCRIPT_DIR"
    
    # Python 스크립트 실행
    python3 "$PYTHON_SCRIPT" \
        --server-name "$SERVER_NAME" \
        --server-ip "$SERVER_IP" \
        --interface "$INTERFACE" \
        --apps-script-url "$APPS_SCRIPT_URL" \
        >> "$LOG_FILE" 2>&1
    
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log "트래픽 모니터 실행 완료"
    else
        log "ERROR: 트래픽 모니터 실행 실패 (exit code: $exit_code)"
        return $exit_code
    fi
}

# 메인 실행
main() {
    log "=== Traffic Monitor Runner 시작 ==="
    
    # 설정 검증
    validate_config
    
    # Git 업데이트
    update_repository
    
    # 모니터 실행
    run_monitor
    local monitor_exit_code=$?
    
    log "=== Traffic Monitor Runner 완료 ==="
    
    # 로그 파일 크기 관리 (100MB 이상이면 백업)
    if [[ -f "$LOG_FILE" ]] && [[ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null) -gt 104857600 ]]; then
        mv "$LOG_FILE" "${LOG_FILE}.backup.$(date +%Y%m%d)"
        log "로그 파일 백업 완료"
    fi
    
    exit $monitor_exit_code
}

# 스크립트 실행
main "$@"