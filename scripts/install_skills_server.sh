#!/bin/bash
# scripts/install_skills_server.sh
# 서버에서 실행: ClawHub 스킬 44개 다운로드 → workspace/skills/ 설치
set -uo pipefail

SKILLS_DIR="$HOME/Agent_Team_Management/openclaw-config/workspace/skills"
mkdir -p "$SKILLS_DIR"

SLUGS=(
  "gog"
  "self-improving-agent"
  "ontology"
  "tavily-search"
  "summarize"
  "github"
  "weather"
  "polymarketodds"
  "notion"
  "nano-banana-pro"
  "nano-pdf"
  "api-gateway"
  "obsidian"
  "humanizer"
  "openai-whisper"
  "mcporter"
  "humanize-ai-text"
  "clawddocs"
  "youtube-api-skill"
  "youtube-watcher"
  "frontend-design"
  "gemini"
  "stock-market-pro"
  "automation-workflows"
  "clawdhub"
  "video-frames"
  "apple-notes"
  "superdesign"
  "n8n-workflow-automation"
  "spotify-player"
  "tmux"
  "microsoft-excel"
  "web-search-plus"
  "markdown-converter"
  "multi-search-engine"
  "playwright-mcp"
  "marketing-skills"
  "gcalcli-calendar"
  "notion-api-skill"
  "google-drive"
  "prompt-engineering-expert"
  "debug-pro"
  "google-sheets"
)

SUCCESS=0
SKIPPED=0
FAILED=()

echo "ClawHub 스킬 설치 시작 (총 ${#SLUGS[@]}개)"
echo "대상 디렉토리: $SKILLS_DIR"
echo "============================================"

for slug in "${SLUGS[@]}"; do
  SKILL_DIR="$SKILLS_DIR/$slug"

  if [ -f "$SKILL_DIR/SKILL.md" ] || [ -f "$SKILL_DIR/skill.md" ]; then
    echo "  ↩ $slug (이미 설치됨)"
    ((SKIPPED++)) || true
    continue
  fi

  echo -n "  ⬇ $slug ... "
  mkdir -p "$SKILL_DIR"

  TMPZIP="/tmp/skill_${slug}.zip"
  HTTP_STATUS=$(curl -s -L -w "%{http_code}" \
    "https://clawhub.ai/api/v1/download?slug=${slug}" \
    -o "$TMPZIP" 2>/dev/null || echo "000")

  if [ "$HTTP_STATUS" = "200" ] && unzip -t "$TMPZIP" > /dev/null 2>&1; then
    unzip -q -o "$TMPZIP" -d "$SKILL_DIR" 2>/dev/null || true

    # zip 내부에 서브디렉토리가 있으면 플래튼
    if [ ! -f "$SKILL_DIR/SKILL.md" ] && [ ! -f "$SKILL_DIR/skill.md" ]; then
      NESTED=$(find "$SKILL_DIR" -maxdepth 2 \( -name "SKILL.md" -o -name "skill.md" \) 2>/dev/null | head -1)
      if [ -n "$NESTED" ]; then
        NESTED_DIR=$(dirname "$NESTED")
        if [ "$NESTED_DIR" != "$SKILL_DIR" ]; then
          cp -r "$NESTED_DIR"/. "$SKILL_DIR/" 2>/dev/null || true
          rm -rf "$NESTED_DIR"
        fi
      fi
    fi

    if [ -f "$SKILL_DIR/SKILL.md" ] || [ -f "$SKILL_DIR/skill.md" ]; then
      echo "✓"
      ((SUCCESS++)) || true
    else
      echo "✗ (SKILL.md 없음)"
      FAILED+=("$slug")
      rm -rf "$SKILL_DIR"
    fi
  else
    echo "✗ (HTTP $HTTP_STATUS)"
    FAILED+=("$slug")
    rm -rf "$SKILL_DIR"
  fi

  rm -f "$TMPZIP"
done

echo "============================================"
echo "완료: 성공 $SUCCESS | 스킵 $SKIPPED | 실패 ${#FAILED[@]}"
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "실패 목록: ${FAILED[*]}"
fi
echo ""
echo "설치된 스킬 목록:"
ls "$SKILLS_DIR"
