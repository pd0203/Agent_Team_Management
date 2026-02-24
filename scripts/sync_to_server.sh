#!/bin/bash
# 로컬 → 서버 설정 파일 동기화 스크립트
set -e

SERVER="ubuntu@168.107.39.89"
KEY="$HOME/.ssh/id_ed25519"
LOCAL="$HOME/Desktop/Agent_Team_Management"
REMOTE="~/Agent_Team_Management"

echo "=== 서버 권한 수정 및 디렉토리 생성 ==="
ssh -i "$KEY" "$SERVER" "
  sudo chmod -R 777 ~/Agent_Team_Management/openclaw-config
  mkdir -p ~/Agent_Team_Management/openclaw-config/workspace/chief-secretary-pro
  mkdir -p ~/Agent_Team_Management/openclaw-config/workspace/skills
"

echo "=== 설정 파일 동기화 ==="
scp -i "$KEY" "$LOCAL/openclaw-config/openclaw.json" "$SERVER:$REMOTE/openclaw-config/openclaw.json"

echo "=== SOUL.md 전체 동기화 ==="
for agent in chief-secretary chief-secretary-pro planning-pm marketer designer finance-manager cs-manager; do
  if [ -f "$LOCAL/openclaw-config/workspace/$agent/SOUL.md" ]; then
    scp -i "$KEY" "$LOCAL/openclaw-config/workspace/$agent/SOUL.md" \
      "$SERVER:$REMOTE/openclaw-config/workspace/$agent/SOUL.md"
    echo "  ✓ $agent/SOUL.md"
  fi
done

echo "=== 스킬 설치 스크립트 전송 ==="
scp -i "$KEY" "$LOCAL/scripts/install_skills_server.sh" "$SERVER:$REMOTE/scripts/install_skills_server.sh"
scp -i "$KEY" "$LOCAL/scripts/install_skills_addon.sh" "$SERVER:$REMOTE/scripts/install_skills_addon.sh"
ssh -i "$KEY" "$SERVER" "chmod +x ~/Agent_Team_Management/scripts/install_skills_server.sh ~/Agent_Team_Management/scripts/install_skills_addon.sh"

echo "=== ClawHub 스킬 다운로드 (서버에서 실행) ==="
ssh -i "$KEY" "$SERVER" "bash ~/Agent_Team_Management/scripts/install_skills_server.sh"

echo "=== 추가 스킬 다운로드 (서버에서 실행) ==="
ssh -i "$KEY" "$SERVER" "bash ~/Agent_Team_Management/scripts/install_skills_addon.sh"

echo "=== 컨테이너 재시작 ==="
ssh -i "$KEY" "$SERVER" "cd ~/Agent_Team_Management && docker compose up -d --force-recreate openclaw-gateway"

echo ""
echo "=== 완료! ==="
