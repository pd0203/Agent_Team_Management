#!/bin/bash
# 추가 스킬 5개 설치 스크립트
set -uo pipefail

SKILLS_DIR="$HOME/Agent_Team_Management/openclaw-config/workspace/skills"
mkdir -p "$SKILLS_DIR"

SLUGS=(
  "gemini-deep-research"
  "topic-monitor"
  "todoist-api"
  "skill-vetter"
  "thinking-partner"
)

SUCCESS=0
FAILED=()

echo "추가 스킬 설치 (${#SLUGS[@]}개)"
echo "========================="

for slug in "${SLUGS[@]}"; do
  SKILL_DIR="$SKILLS_DIR/$slug"

  if [ -f "$SKILL_DIR/SKILL.md" ] || [ -f "$SKILL_DIR/skill.md" ]; then
    echo "  ↩ $slug (이미 설치됨)"
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

echo "========================="
echo "완료: 성공 $SUCCESS | 실패 ${#FAILED[@]}"
[ ${#FAILED[@]} -gt 0 ] && echo "실패: ${FAILED[*]}"
