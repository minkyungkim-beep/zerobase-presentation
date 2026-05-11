# ZeroDeck 봇 셋업 가이드 (관리자용)

처음 한 번만 진행하시면 됩니다. 약 1~2시간 소요.

---

## 0. 준비물 체크

- [ ] Slack 워크스페이스 **관리자 권한**
- [ ] **Google Cloud 계정** (없으면 https://cloud.google.com 무료 가입, 신용카드 등록 필요하나 무료 티어로 사용)
- [ ] **Anthropic API 키** (https://console.anthropic.com — Claude 사용)
- [ ] **GitHub Personal Access Token** (이미 발급한 토큰 재사용 가능)

---

## 1. Slack 앱 등록 (10분)

1. https://api.slack.com/apps → **Create New App** → **From a manifest**
2. 워크스페이스 선택 (day1company)
3. `slack_bot/slack_app_manifest.yaml` 파일 내용을 통째로 복사 → 붙여넣기 → **Next** → **Create**
4. 좌측 메뉴 → **OAuth & Permissions** → **Install to Workspace**
5. 권한 동의 → 설치 완료
6. 다음 토큰들 메모 (시크릿 등록할 때 씀):
   - **Bot User OAuth Token** (xoxb-...로 시작) — `OAuth & Permissions` 페이지 상단
   - **Signing Secret** — `Basic Information` → `App Credentials` 안

---

## 2. Google Cloud 셋업 (20분)

### 2-1. gcloud CLI 설치 (한 번만)

```bash
# macOS
brew install --cask google-cloud-sdk
gcloud init
gcloud auth login
```

### 2-2. 프로젝트 생성

```bash
export PROJECT_ID=zerobase-deck-bot
gcloud projects create $PROJECT_ID --name="ZeroBase Deck Bot"
gcloud config set project $PROJECT_ID
```

→ 결제 계정 연결 필요 (콘솔에서 클릭). **무료 티어 안에서 충분**.

### 2-3. 필요한 API 활성화

```bash
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com
```

### 2-4. 시크릿 등록 (4개)

```bash
# Slack 토큰들 (1번에서 복사한 값)
echo -n "xoxb-..." | gcloud secrets create zerodeck-slack-bot-token --data-file=-
echo -n "abc123..." | gcloud secrets create zerodeck-slack-signing-secret --data-file=-

# Claude API 키
echo -n "sk-ant-..." | gcloud secrets create zerodeck-anthropic-key --data-file=-

# GitHub 토큰
echo -n "ghp_..." | gcloud secrets create zerodeck-github-token --data-file=-
```

### 2-5. Cloud Run 서비스 어카운트에 시크릿 접근 권한

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in zerodeck-slack-bot-token zerodeck-slack-signing-secret zerodeck-anthropic-key zerodeck-github-token; do
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:$SA" \
        --role="roles/secretmanager.secretAccessor"
done
```

---

## 3. 배포 (10분)

```bash
cd ~/Documents/Claude/Projects/PPT\ 자동\ 생성\ +\ 디자인
chmod +x slack_bot/cloudrun_deploy.sh
export PROJECT_ID=zerobase-deck-bot
./slack_bot/cloudrun_deploy.sh
```

빌드/배포가 끝나면 URL 출력됨:
```
✅ 배포 완료!
   URL: https://zerodeck-bot-XXXXXX.a.run.app
```

이 URL을 메모.

---

## 4. Slack 앱 → Cloud Run URL 연결 (5분)

https://api.slack.com/apps → 만든 앱 선택 → 다음 3곳 모두 동일 URL로 설정:

| 위치 | Request URL |
|------|-------------|
| **Event Subscriptions** | `https://YOUR-URL/slack/events` |
| **Interactivity & Shortcuts** | `https://YOUR-URL/slack/events` |
| **Slash Commands → 각 명령어** (3개) | `https://YOUR-URL/slack/events` |

각각 저장 (`Save Changes`).

마지막으로 **Install App** → **Reinstall to Workspace** (권한 변경 시 재설치).

---

## 5. 테스트 (5분)

봇을 사용하려는 채널에 초대:
```
/invite @ZeroDeck
```

테스트:
```
/제로덱-도움말
```
→ 도움말 메시지가 떠야 정상.

```
/제로덱 테스트 자료, 5장
```
→ 1~2분 후 PPTX/PDF + 링크 회신.

---

## 6. 팀원에게 공유

[`team_usage_guide.md`](team_usage_guide.md) 1페이지 짜리 사용법을 사내 채널에 공유.

---

## 트러블슈팅

| 문제 | 해결 |
|------|------|
| `URL verification failed` | Event Subscriptions URL이 정확한지 확인. Cloud Run이 깨어있는지 확인 (`/health` 호출) |
| `dispatch_failed` 메시지 | 시크릿 값이 정확한지, 만료되지 않았는지 확인 |
| AI 생성 실패 | Claude API 키 유효성 + 잔액 확인 |
| 빌드 timeout | Cloud Run timeout을 600초로 (이미 설정됨) |
| 한글 깨짐 | Dockerfile의 Pretendard 설치 단계 로그 확인 |

문제 있으면 Cloud Run 콘솔 → **Logs**에서 에러 확인.

---

## 비용 견적

- **Cloud Run**: 무료 티어 안 (월 200만 요청 무료 — 우리는 100건도 안 됨)
- **Cloud Build**: 빌드 1회 ~5분, 무료 티어 일 120분
- **Secret Manager**: 무료 티어 충분
- **Anthropic API**: 슬라이드 1세트 ~$0.05~0.10 (Sonnet 기준)
- **GitHub**: 무료

월 50건 사용 가정: **~$3 내외** (Anthropic 비용만)
