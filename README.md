# admin_network_traffic_monitoring_system


## 1. 스크립트 설정

먼저 `run_traffic_monitor.sh` 파일에서 다음 설정값들을 실제 환경에 맞게 수정해야 합니다:

```bash
# 설정 - 사용자가 수정해야 하는 부분
SERVER_NAME="web-server-01"                # 서버 식별명
SERVER_IP="210.94.179.180"                  # 서버 IP 주소
INTERFACE="eno1"                         # 모니터링할 네트워크 인터페이스
APPS_SCRIPT_URL="https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec"  # Apps Script URL

# 스크립트 경로 설정
SCRIPT_DIR="/home/user/traffic-monitor"     # Git 저장소가 clone된 로컬 경로
```

### 네트워크 인터페이스 확인 방법

사용 가능한 네트워크 인터페이스를 확인하려면:

```bash
# 방법 1: ip 명령어 사용
ip link show

# 방법 2: vnstat으로 확인
vnstat --iflist

# 방법 3: ifconfig 사용 (구 버전)
ifconfig
```

일반적인 인터페이스 이름:
- **유선**: `eth0`, `eno1`, `enp3s0`
- **무선**: `wlan0`, `wlp12s0`, `wlo1`

## 2. 스크립트 권한 설정

실행 권한을 부여합니다:

```bash
chmod +x run_traffic_monitor.sh
```

## 3. 수동 테스트

Cron Job 설정 전에 스크립트가 정상 동작하는지 확인:

```bash
./run_traffic_monitor.sh
```

로그 확인:

```bash
tail -f /var/log/traffic-monitor/traffic_monitor.log
```

## 4. Cron Job 설정

### 4.1 Crontab 편집

```bash
crontab -e
```

### 4.2 모니터링 주기별 설정

#### 10분마다 실행 (권장)

```bash
# 10분마다 트래픽 모니터링 실행
*/10 * * * * /path/to/run_traffic_monitor.sh
```

#### 5분마다 실행 (더 민감한 감지)

```bash
# 5분마다 트래픽 모니터링 실행
*/5 * * * * /path/to/run_traffic_monitor.sh
```

#### 15분마다 실행 (부하 절약)

```bash
# 15분마다 트래픽 모니터링 실행
*/15 * * * * /path/to/run_traffic_monitor.sh
```

### 4.3 로그 관리가 포함된 설정 (권장)

시스템 로그와 별도로 Cron 실행 로그를 관리하려면:

```bash
# 10분마다 실행하고 Cron 로그 별도 저장
*/10 * * * * /path/to/run_traffic_monitor.sh >> /var/log/traffic-monitor/cron.log 2>&1
```

### 4.4 실제 설정 예시

실제 경로를 포함한 완전한 예시:

```bash
# 매 10분마다 네트워크 트래픽 모니터링 실행
*/10 * * * * /home/admin/scripts/run_traffic_monitor.sh >> /var/log/traffic-monitor/cron.log 2>&1
```

## 5. Cron Job 확인

### 5.1 설정된 Cron Job 확인

```bash
crontab -l
```

### 5.2 Cron 서비스 상태 확인

```bash
# Ubuntu/Debian
sudo systemctl status cron

# CentOS/RHEL
sudo systemctl status crond
```

### 5.3 Cron 로그 확인

```bash
# 시스템 Cron 로그
sudo tail -f /var/log/cron

# 또는 syslog에서 cron 관련 로그
sudo grep CRON /var/log/syslog
```

## 6. 로그 모니터링

### 6.1 실시간 로그 확인

```bash
# 메인 로그 확인
tail -f /var/log/traffic-monitor/traffic_monitor.log

# Cron 실행 로그 확인
tail -f /var/log/traffic-monitor/cron.log
```

### 6.2 로그 파일 위치

- **메인 로그**: `/var/log/traffic-monitor/traffic_monitor.log`
- **Cron 로그**: `/var/log/traffic-monitor/cron.log`
- **백업 로그**: `/var/log/traffic-monitor/traffic_monitor.log.backup.YYYYMMDD`

## 7. 문제 해결

### 7.1 Cron Job이 실행되지 않는 경우

1. **절대 경로 사용 확인**:
   ```bash
   # 잘못된 예
   */10 * * * * ./run_traffic_monitor.sh
   
   # 올바른 예
   */10 * * * * /home/user/scripts/run_traffic_monitor.sh
   ```

2. **실행 권한 확인**:
   ```bash
   ls -la /path/to/run_traffic_monitor.sh
   # -rwxr-xr-x 권한이 있어야 함
   ```

3. **환경 변수 문제**:
   Cron 환경에서는 PATH가 제한적이므로, 스크립트 내에서 절대 경로 사용

### 7.2 스크립트 오류 확인

```bash
# 최근 에러 로그 확인
grep "ERROR" /var/log/traffic-monitor/traffic_monitor.log

# Python 관련 오류 확인
grep "python3" /var/log/traffic-monitor/cron.log
```

### 7.3 디버그 모드 실행

문제 진단을 위해 디버그 모드로 한 번 실행:

```bash
# 스크립트 내 Python 실행 부분에 --debug 옵션 임시 추가
python3 "$PYTHON_SCRIPT" \
    --server-name "$SERVER_NAME" \
    --server-ip "$SERVER_IP" \
    --interface "$INTERFACE" \
    --apps-script-url "$APPS_SCRIPT_URL" \
    --debug \
    >> "$LOG_FILE" 2>&1
```

## 8. 모니터링 확인

Cron Job 설정 후 다음을 확인하여 정상 동작 여부를 검증:

1. **Health Check 메시지**: 스크립트 로그에서 "Health check sent successfully" 메시지 확인
2. **Slack 알림**: Apps Script를 통해 Slack 채널에 알림이 오는지 확인
3. **파일 생성**: `traffic_history.json` 파일이 생성되고 업데이트되는지 확인

### 확인 명령어

```bash
# 최근 실행 로그 확인
tail -20 /var/log/traffic-monitor/traffic_monitor.log

# Health check 성공 로그 확인
grep "Health check sent successfully" /var/log/traffic-monitor/traffic_monitor.log

# 히스토리 파일 확인
ls -la /path/to/traffic-monitor/traffic_history.json
```

정상 동작 시 Health Check는 설정된 주기마다 성공적으로 전송되며, 이상치 감지 시에만 Slack으로 스파이크 알림이 전송됩니다.