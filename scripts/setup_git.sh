#!/usr/bin/env bash
# 첫 1회 실행: 워크스페이스 폴더를 zerobase-presentation 레포와 연결.
# 사용:
#   cd "/Users/.../PPT 자동 생성 + 디자인"
#   bash scripts/setup_git.sh
set -euo pipefail

REMOTE="https://github.com/minkyungkim-beep/zerobase-presentation.git"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

echo "[1/5] git 초기화"
if [ ! -d ".git" ]; then
  git init -b main
else
  echo "  (이미 git repo)"
fi

echo "[2/5] remote 'origin' 설정"
if git remote | grep -q "^origin$"; then
  git remote set-url origin "$REMOTE"
else
  git remote add origin "$REMOTE"
fi
git remote -v

echo "[3/5] macOS Keychain에 PAT 저장 설정"
git config --global credential.helper osxkeychain || true
git config user.name  "$(git config --global user.name  || echo '밍')"
git config user.email "$(git config --global user.email || echo 'minkyungkim@day1company.co.kr')"

echo "[4/5] 원격 fetch (충돌 확인)"
if git fetch origin 2>/dev/null; then
  REMOTE_BRANCH="$(git ls-remote --heads origin | head -1 | awk -F'refs/heads/' '{print $2}' | tr -d ' \n')"
  if [ -n "${REMOTE_BRANCH:-}" ]; then
    echo "  원격 브랜치: $REMOTE_BRANCH"
    git checkout -B "$REMOTE_BRANCH" 2>/dev/null || true
    if git rev-parse --verify "origin/$REMOTE_BRANCH" >/dev/null 2>&1; then
      git pull --rebase origin "$REMOTE_BRANCH" || \
        git pull --allow-unrelated-histories --no-edit origin "$REMOTE_BRANCH" || true
    fi
  else
    echo "  원격이 비어 있음 — 첫 커밋부터 시작"
  fi
else
  echo "  fetch 실패 (PAT 미설정일 수 있음). 4단계는 건너뜀."
fi

echo "[5/5] 초기 커밋 (소스 + README)"
git add -A
if git diff --cached --quiet; then
  echo "  (커밋할 변경 없음)"
else
  git commit -m "[init] 자동 생성 시스템 초기 셋업 — design_system + scripts + README"
fi

echo
echo "완료. 첫 푸시는 다음 명령으로 (PAT 한 번 입력):"
echo "  git push -u origin main"
echo
echo "이후부터는: python3 scripts/git_push.py inputs/<파일>.json"
