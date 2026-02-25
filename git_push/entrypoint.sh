#!/bin/sh
# HOME을 /tmp로 설정하여 git config / credentials 저장 경로 확보
export HOME=/tmp
mkdir -p "$HOME"

# GitHub 인증 설정 (GITHUB_TOKEN 환경변수 사용)
printf 'https://x-access-token:%s@github.com\n' "$GITHUB_TOKEN" > "$HOME/.git-credentials"
git config --global credential.helper store
git config --global user.name "${GIT_AUTHOR_NAME:-AI Agent Team}"
git config --global user.email "${GIT_AUTHOR_EMAIL:-agent@hyojin.ai}"

exec "$@"
