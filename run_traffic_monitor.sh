#!/bin/bash

# ===== Traffic Monitor Runner Script =====
# Git pull and run traffic monitor with user configuration
# Usage: ./run_traffic_monitor.sh

# 설정 - 사용자가 수정해야 하는 부분
SERVER_NAME="your-server-name"         # 예: "web-server-01"
SERVER_IP="your-server-ip"             # 예: "192.168.1.100"
INTERFACE="your-interface"             # 예: "wlp12s0" 또는 "eth0"
APPS_SCRIPT_URL="your-apps-script-url"  # 예: "https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec"

# 스크립트 경로 설정
SCRIPT_DIR="/path/to/traffic-monitor"  # Git 저장소가 clone된 로컬 디렉토리 경로
PYTHON_SCRIPT="traffic_monitor.py"
LOG_DIR="/var/log/traffic-monitor"
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
    
    if [[ ! -d "$SCRIPT_DIR" ]]; then
        error_exit "스크립트 디렉토리가 존재하지 않습니다: $SCRIPT_DIR"
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