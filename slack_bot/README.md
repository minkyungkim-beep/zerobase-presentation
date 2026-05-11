# ZeroBase Deck Bot — Slack 봇

팀원이 Slack에서 PPT를 자동으로 만들 수 있게 하는 슬랙봇.

---

## 구조 (아키텍처)

```
   Slack Workspace                         Google Cloud Run                 GitHub
─────────────────                       ─────────────────────             ──────────
  팀원 입력                               Bolt 서버 (Python)                 저장소
  ─────────                               ─────────────────                  ────────
  1) /제로덱 명령어                        ┌────────────────┐               ┌──────────┐
  2) @ZeroDeck 멘션          ─────▶       │  Slack Bolt    │  ─push──▶    │ inputs/  │
  3) JSON 파일 업로드                      │  - slash cmd   │              │ outputs/ │
  4) 자연어 메시지                         │  - app mention │              │ decks/   │
                                          │  - file upload │              └──────────┘
                                          │  - modal form  │                    │
                                          └───────┬────────┘                    │
                                                  │                             ▼
                                                  ▼                       GitHub Pages
                                          ┌────────────────┐              ─────────────
                                          │  Build Pipeline│              ${stem}.html
                                          │  - render_html │              (즉시 미리보기)
                                          │  - build_pptx  │
                                          │  - html_to_pdf │
                                          └───────┬────────┘
                                                  │
                                                  ▼
                                          ┌────────────────┐
                                          │ AI Generator   │
                                          │ (Claude API)   │
                                          │ Case 2 전용     │
                                          └───────┬────────┘
                                                  │
                                                  ▼
                                          ┌────────────────┐
                                          │ Slack 회신      │
                                          │ - PPTX 첨부     │
                                          │ - PDF 첨부      │
                                          │ - HTML 링크     │
                                          └────────────────┘
```

---

## 입력 방식 4가지 (한 봇에서 다 지원)

### 1) 슬래시 커맨드 — 가장 간단
```
/제로덱 자기소개서 작성법, 신입 취준생 대상, 8장
```
→ 자연어 한 줄 + AI가 해석해서 생성

### 2) 앱 멘션 — 대화형
```
@ZeroDeck 자기소개서 강의 자료 만들어줘
↓ 봇 회신
주제: 자기소개서 작성법
대상: ?
슬라이드 수: ?
이렇게 진행할까요? 모달로 자세히 입력하시려면 [폼 열기] 버튼을 눌러주세요.
```

### 3) 모달 폼 — 정밀 입력
```
[폼 열기 버튼 또는 /제로덱-폼]
─────────────────────────────
주제: ___________
대상: ___________
챕터 1 제목: ___________
챕터 1 내용: ___________
[+ 챕터 추가]
이미지 첨부: [파일 선택]
─────────────────────────────
[제출]
```

### 4) JSON 파일 업로드 — 개발자 친화
```
파워유저가 JSON 파일을 채널에 첨부 + "/제로덱-빌드" 코멘트
→ 봇이 받아서 그대로 빌드
```

---

## Case 1·2 분기 로직

```python
if 입력에 "참고자료 PDF/Notion 링크/구글파일" 포함:
    → Case 2 (AI 콘텐츠 생성 + 디자인 적용)
       1. RAG로 합격자 핵심 성과 추출
       2. 기존 자료 톤·구조 학습
       3. 새 슬라이드 스크립트 생성
       4. JSON 변환 → 빌드
elif JSON 파일 직접 업로드:
    → Case 1 (디자인 자동화만)
       1. JSON → render_html.py / build_pptx.py 직행
elif 자연어 한 줄 / 폼 입력:
    → Case 1 또는 Case 2 (사용자가 선택 가능, 기본 Case 2)
```

---

## 호스팅: Google Cloud Run 추천 이유

| 후보 | 장점 | 단점 | 우리 케이스 적합도 |
|------|------|------|------------------|
| **Cloud Run** ⭐ | 서버리스 (사용량만 과금), 60분 timeout, Docker 지원, 무료 티어 ~2M 요청/월 | 학습곡선 약간 | **★★★★★** Playwright + python-pptx가 무거워 Docker 필요 |
| Vercel Functions | 가장 간단 | 10초 timeout (PDF 변환 1~3초 걸려서 빠듯) | ★★ |
| Render | 간단, GitHub 연동 | 무료는 sleep, 워크로드 무거우면 유료 ($7~) | ★★★★ |
| Mac 자체 호스팅 | 비용 0원 | Mac 잠자면 중단, 외부 노출에 ngrok 필요 | ★★ (개발용) |

**Cloud Run 비용 견적**: 무료 티어 안에서 충분 (월 200만 요청 무료). 실 사용량 50~100건/월 → **$0**.

---

## 셋업 단계

### Phase 1 — 셋업 (사용자 작업, 30~60분)
1. **Slack 앱 등록** — `slack_app_manifest.yaml` 사용
2. **Google Cloud 계정 생성** — `gcloud` CLI 설치
3. **환경 변수 secret 등록** (Slack 토큰, Claude API 키 등)
4. **GitHub Personal Access Token** 발급 (코드 push용)

### Phase 2 — 배포 (Claude가 도와드림, 1~2시간)
1. Docker 이미지 빌드
2. Cloud Run 배포 명령어 1줄
3. Slack 앱에 Cloud Run URL 등록
4. 테스트

### Phase 3 — 팀원 온보딩 (총 5분)
1. Slack에 봇 초대
2. 1~2개 채널 추가
3. 사용 가이드 1페이지 공유

---

## 다음 산출물 (이 폴더에 들어갈 파일들)

- [ ] `slack_app_manifest.yaml` — Slack 앱 정의 (한 번에 등록)
- [ ] `app.py` — Bolt 메인 (slash, mention, file, modal 모두 라우팅)
- [ ] `handlers/file_upload.py` — JSON 파일 → 빌드
- [ ] `handlers/natural_language.py` — 자연어 → AI → JSON → 빌드
- [ ] `handlers/modal.py` — 폼 입력 → 빌드
- [ ] `ai/generator.py` — Claude API로 슬라이드 스크립트 생성 (Case 2)
- [ ] `ai/prompt_template.md` — AI에 줄 시스템 프롬프트
- [ ] `Dockerfile` — Playwright + fonts + Python 환경
- [ ] `cloudrun_deploy.sh` — 배포 스크립트
- [ ] `team_usage_guide.md` — 팀원에게 공유할 가이드

---

## 진행 순서 (제안)

**Step 1 (오늘)** — 매니페스트 + 봇 코드 골격 작성 (Claude)
**Step 2 (사용자)** — Slack 앱 생성 + Cloud 계정 준비
**Step 3 (Claude)** — 배포 스크립트 + 첫 테스트
**Step 4 (Claude)** — AI 생성 모듈 + 다양한 입력 모드 통합
**Step 5 (팀)** — 점진적 사용 + 피드백 반영
