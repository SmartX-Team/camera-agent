#!/bin/bash

INTERFACE=$(ip -o -4 route show to default | awk '{print $5}')
echo "Using interface: $INTERFACE"

# PTPd 실행 및 로그 파일로 출력
/usr/local/sbin/ptpd2 -M -i "$INTERFACE" -V > /var/log/ptpd.log 2>&1 &

# PTPd 프로세스 ID 저장
PID=$!

# PTPd 프로세스 상태 확인 함수
check_ptpd() {
    if ps -p $PID > /dev/null
    then
        echo "PTPd is running."
        return 0
    else
        echo "PTPd has stopped. Check log file for details."
        return 1
    fi
}

# 초기 상태 확인
sleep 5
if ! check_ptpd; then
    echo "PTPd failed to start. Exiting."
    exit 1
fi

echo "PTPd started successfully. Monitoring..."

# 주기적으로 PTPd 상태 확인
while true; do
    sleep 60
    if ! check_ptpd; then
        echo "PTPd has stopped unexpectedly. Restarting..."
        /usr/local/sbin/ptpd2 -M -i "$INTERFACE" -V > /var/log/ptpd.log 2>&1 &
        PID=$!
        sleep 5
        if ! check_ptpd; then
            echo "Failed to restart PTPd. Exiting."
            exit 1
        fi
    fi
done