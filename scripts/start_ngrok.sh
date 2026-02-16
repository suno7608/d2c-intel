#!/usr/bin/env bash
# ngrok 자동 시작 + 자동 재시작 스크립트
# LaunchD 대신 이 스크립트를 사용

DOMAIN="hesitative-discographically-erma.ngrok-free.dev"
PORT=8090
LOG="/Users/soonho/Documents/New project/d2c-intel/logs/ngrok_live.log"

while true; do
    echo "[$(date)] Starting ngrok..." >> "$LOG"
    /opt/homebrew/bin/ngrok http "$PORT" --domain="$DOMAIN" --pooling-enabled --log="$LOG" 2>&1
    echo "[$(date)] ngrok exited. Restarting in 10s..." >> "$LOG"
    sleep 10
done
