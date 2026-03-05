#!/usr/bin/env bash
WATCH_FILE="/home/node/.openclaw/workspace/chief-secretary/SOUL.md"
LAST_SUM=""
while true; do
  if [ -f "$WATCH_FILE" ]; then
    SUM=$(md5sum "$WATCH_FILE" | awk '{print $1}')
    if [ "$SUM" != "$LAST_SUM" ]; then
      LAST_SUM="$SUM"
      MSG="update: SOUL.md 자동 푸시 (감지: $(date -u +%Y-%m-%dT%H:%M:%SZ))"
      curl -s -X POST http://agent-git-push:7777/push -H "Content-Type: application/json" -d "{\"message\":\"$MSG\"}"
    fi
  fi
  sleep 3
done
