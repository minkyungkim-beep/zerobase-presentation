#!/usr/bin/env bash
# ZeroDeck 봇 — Cloud Run 배포 스크립트.
#
# 사전 조건:
#   1) Google Cloud 계정 + 프로젝트 ID
#   2) gcloud CLI 설치 + 로그인 완료
#   3) 환경 변수 설정 (아래)

set -euo pipefail

# ─────────────────────────────────────────────────────
# 사용자가 채워야 할 변수
# ─────────────────────────────────────────────────────
PROJECT_ID="${PROJECT_ID:?GCP 프로젝트 ID를 설정하세요. 예: export PROJECT_ID=my-zerobase}"
REGION="${REGION:-asia-northeast3}"          # 서울
SERVICE_NAME="${SERVICE_NAME:-zerodeck-bot}"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# 시크릿 (Secret Manager 사용 권장)
SLACK_BOT_TOKEN_SECRET="${SLACK_BOT_TOKEN_SECRET:-zerodeck-slack-bot-token}"
SLACK_SIGNING_SECRET_NAME="${SLACK_SIGNING_SECRET_NAME:-zerodeck-slack-signing-secret}"
ANTHROPIC_API_KEY_SECRET="${ANTHROPIC_API_KEY_SECRET:-zerodeck-anthropic-key}"
GITHUB_TOKEN_SECRET="${GITHUB_TOKEN_SECRET:-zerodeck-github-token}"

# ─────────────────────────────────────────────────────
echo "🚀 ZeroDeck Bot — Cloud Run 배포 시작"
echo "PROJECT_ID  = $PROJECT_ID"
echo "REGION      = $REGION"
echo "SERVICE     = $SERVICE_NAME"
echo "IMAGE       = $IMAGE"
echo

# 1) Docker 이미지 빌드 (Cloud Build 사용 — 로컬 Docker 불필요)
echo "📦 Cloud Build로 이미지 빌드..."
gcloud builds submit \
    --tag "$IMAGE" \
    --project "$PROJECT_ID" \
    --timeout=20m \
    -f slack_bot/Dockerfile .

# 2) Cloud Run 배포
echo "🌐 Cloud Run에 배포..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --platform managed \
    --memory 2Gi \
    --cpu 2 \
    --timeout 600s \
    --concurrency 4 \
    --max-instances 5 \
    --allow-unauthenticated \
    --set-secrets "SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN_SECRET}:latest" \
    --set-secrets "SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET_NAME}:latest" \
    --set-secrets "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY_SECRET}:latest" \
    --set-secrets "GITHUB_TOKEN=${GITHUB_TOKEN_SECRET}:latest" \
    --set-env-vars "GITHUB_REPO=minkyungkim-beep/zerobase-presentation"

URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" --project "$PROJECT_ID" \
    --format "value(status.url)")

echo
echo "✅ 배포 완료!"
echo "   URL: $URL"
echo
echo "👉 다음 단계 (수동):"
echo "   1) https://api.slack.com/apps 에서 앱 선택"
echo "   2) Event Subscriptions → Request URL: ${URL}/slack/events"
echo "   3) Slash Commands → 각 명령어 Request URL: ${URL}/slack/events"
echo "   4) Interactivity → Request URL: ${URL}/slack/events"
echo "   5) Save & Reinstall App"
