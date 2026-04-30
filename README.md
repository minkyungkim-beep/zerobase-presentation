# 제로베이스 설명회 자료 자동 생성

매주 반복되는 온라인/오프라인 설명회 덱 제작을 자동화하는 시스템.
디자인 시스템 v1.0 기준, **Case 1 (디자인 자동화 모드)** 까지 구축되어 있음.

---

## 폴더 구조

```
.
├── design_system/
│   ├── tokens.json     ← 컬러·타이포·간격 단일 진실 소스
│   └── base.css        ← HTML 미리보기용 CSS
├── templates/          ← (예약) 추가 슬라이드 템플릿용
├── inputs/
│   └── sample_slides.json   ← 입력 예시 (JSON 스키마는 아래 참고)
├── scripts/
│   ├── render_html.py  ← JSON → HTML
│   └── build_pptx.py   ← JSON → 편집 가능 PPTX (python-pptx)
├── build.py            ← 단일 진입점 (HTML / PPTX / PDF 동시 생성)
└── outputs/            ← 결과물 (HTML, PPTX, PDF)
```

---

## 매주 사용하는 워크플로우 (Case 1)

1. `inputs/` 폴더에 `2026-05-06_3부.json` 같은 이름으로 새 파일을 만든다.
   → `inputs/sample_slides.json`을 복사해서 텍스트만 바꾸면 됨.
2. 터미널에서:
   ```bash
   python3 build.py inputs/2026-05-06_3부.json
   ```
3. `outputs/2026-05-06_3부.pptx` 가 생성됨 → PowerPoint/Keynote에서 열어 확인 후 그대로 사용.
4. 미리보기가 필요하면 `outputs/2026-05-06_3부.html`을 브라우저로 직접 오픈
   (Pretendard 웹폰트가 자동 로드됨).

옵션:
```bash
python3 build.py inputs/X.json --no-pdf       # PDF 생성 생략
python3 build.py inputs/X.json --out 다른경로  # 출력 폴더 변경
```

---

## JSON 입력 스키마

```json
{
  "meta": {
    "title": "강연 메인 제목",
    "title_em": "강조될 두 번째 줄 (브랜드 네이비로 표시)",
    "subtitle": "한 줄 부제",
    "event_label": "ZEROBASE 온라인 설명회",
    "date": "2026.05.06 (화) 21:00",
    "session": "3부",
    "talk_title_in_footer": "푸터에 들어갈 강연 타이틀",
    "speaker": {
      "name": "라이언",
      "title": "전 OO그룹 인사팀장 · 현 ZeroBase 멘토",
      "bio": ["3~5줄의 약력"]
    }
  },
  "slides": [ /* 아래 6가지 타입 중 하나씩 */ ]
}
```

### 슬라이드 타입 6종

| type | 용도 | 주요 필드 |
|---|---|---|
| `cover` | 표지 (meta에서 자동 채움) | (필드 없음) |
| `chapter_divider` | 챕터 구분 슬라이드 | `ch`, `title`, `sub` |
| `content` | 본문 (제목 + 리드 + 불릿 0~5개) | `chapter`, `title`, `lede`, `bullets[]` |
| `card_grid_4` | 4-up 파스텔 카드 그리드 | `cards[{num,title,items[]}]` |
| `stage_flow` | 스텝 박스 + 화살표 (4~5단계) | `steps[{num,name,desc}]`, `highlight_index` |
| `alert_close` | 마무리 슬라이드 (빨강 강조) | `lede`, `alert` |

### 인라인 마크업

`title`과 `alert` 필드 안에서:
- `<em>강조</em>` → 브랜드 네이비 색상 적용
- `<b>두꺼운 텍스트</b>` → 볼드 처리
- 줄바꿈은 `\n`

---

## 디자인 시스템 토큰을 바꾸고 싶을 때

1. `design_system/tokens.json` 수정 → PPTX 출력에 반영됨.
2. `design_system/base.css`도 같이 동기화 → HTML 미리보기에 반영됨.

> ⚠️ 두 파일은 같은 의미를 표현하므로, 한쪽만 바꾸면 PPTX와 HTML이 달라 보일 수 있음.
> 향후 빌드 단계에서 `tokens.json`에서 CSS를 자동 생성하도록 통합 예정.

---

## 의존성

```bash
pip3 install python-pptx markitdown[pptx]
# PDF 변환은 LibreOffice가 깔려있으면 자동
brew install --cask libreoffice  # macOS
```

---

## 이미지 / 사진 넣기

이미지는 프로젝트 루트의 **`assets/`** 폴더에 두고 JSON에서 경로로 참조합니다.

```
assets/
├── kimjungkeun.jpg       ← 강사 사진
├── kt_portfolio_1.png    ← 합격 포트폴리오 캡처
└── catch_calendar_4.png  ← 캐치 채용 달력
```

JSON에서:
```json
{ "image": "assets/kt_portfolio_1.png" }
```
→ HTML 미리보기와 PPTX 양쪽에 자동 반영됨. 비율은 보존, 가용 영역에 자동 맞춤.

### 이미지 슬라이드 타입 3종

| 타입 | 용도 | 필드 |
|---|---|---|
| `image_full` | 풀-블리드 이미지 + 캡션 | `image`, `caption`, `bg`(`"light"` 또는 생략) |
| `image_headed` | 챕터+제목+리드 위에, 이미지 본문 | `chapter`, `title`, `lede`, `image` |
| `image_split` | 좌·우 분할 (이미지 + 분석) | `chapter`, `title`, `image`, `image_position`(`"left"`/`"right"`), `body_title`, `body_lede`, `items[]` |

### 강사 사진

`speaker` 슬라이드의 placeholder(이름 첫 글자)를 실제 사진으로 바꾸려면:
```json
"speaker": {
  "name": "김준근",
  "title": "AI/DX 전문 컨설턴트",
  "photo": "assets/kimjungkeun.jpg",
  "tags": [ ... ],
  "bio": [ ... ]
}
```

지원 포맷: PNG · JPG · JPEG (정적). [📊 데모 보기](outputs/image_demo.html)

---

## 브라우저에서 바로 텍스트 수정하기

HTML 미리보기 화면에서 **`E` 키**를 누르거나 좌상단 **✏️ 편집 (E)** 버튼을 클릭하면 인라인 편집 모드가 켜져요.

1. 슬라이드의 텍스트 부분을 클릭 → 바로 수정
2. 상단 바의 **💾 JSON 저장** 클릭 → 변경된 JSON 파일이 다운로드됨
3. 다운받은 파일을 `inputs/` 폴더에 옮기고(같은 이름이면 덮어쓰기), 다시 빌드:
   ```bash
   python3 build.py inputs/2026-05-08_3부.json
   ```
   → 수정 사항이 반영된 PPTX·HTML이 새로 생성됨.

조작법:
- `E` 키 — 편집 모드 토글
- `↺ 되돌리기` — 모든 편집을 원본 JSON으로 복구
- 편집 모드에서 텍스트 입력 중에는 좌우 키가 슬라이드 이동 대신 커서 이동으로 동작 (자연스럽게 타이핑 가능)
- 강조(<em>)나 볼드(<b>) 마크업이 들어 있는 제목은 HTML 그대로 보존됨

> 💡 워크플로우 팁: 빠른 문구 수정·오타 수정은 브라우저에서, 슬라이드 추가/삭제·구조 변경은 JSON 파일 직접 편집이 편해요.

---

## GitHub 자동 업로드

레포: https://github.com/minkyungkim-beep/zerobase-presentation

### 첫 1회 셋업 (5분)

1. GitHub에서 Personal Access Token(PAT) 발급
   → Settings → Developer settings → Personal access tokens → Tokens (classic)
   → `repo` 권한 체크 → 토큰 복사 (한 번만 보임)
2. 워크스페이스 폴더에서 셋업 스크립트 실행:
   ```bash
   cd "/Users/.../PPT 자동 생성 + 디자인"
   bash scripts/setup_git.sh
   ```
3. 첫 푸시 — 이때만 username/PAT 입력 (이후 macOS Keychain에 자동 저장):
   ```bash
   git push -u origin main
   # Username: minkyungkim-beep
   # Password: <위에서 복사한 PAT 붙여넣기>
   ```

### 매주 1회 사용

```bash
# 빌드 + 자동 커밋 + 푸시까지 한 번에
python3 scripts/git_push.py inputs/2026-05-06_3부.json
```

→ 이렇게 처리됩니다:
```
1. build.py 실행 → outputs/ 에 HTML/PPTX/PDF 생성
2. presentations/2026-05/2026-05-06_온라인설명회_3부.pptx (.html .pdf .json) 로 복사
3. git commit -m "[2026-05-06] 설명회_자료_생성 — 대기업 면접관이 직접 말하는…"
4. git push
```

옵션:
```bash
python3 scripts/git_push.py inputs/X.json --no-build   # 빌드 건너뛰기
python3 scripts/git_push.py inputs/X.json --no-push    # commit까지만
```

### 경로 규칙

```
presentations/
└── 2026-05/                          ← {YYYY-MM}
    ├── 2026-05-06_온라인설명회_3부.pptx
    ├── 2026-05-06_온라인설명회_3부.html
    ├── 2026-05-06_온라인설명회_3부.pdf
    └── 2026-05-06_온라인설명회_3부.json   (입력 스냅샷)
```

타입 자동 감지 키워드: `오프라인` → 오프라인설명회 / `박람회` → 온라인박람회 / `세미나` → 직무세미나 / `그룹상담` / 그 외 → 온라인설명회. 파일명 또는 `meta.session`에 포함만 시키면 됨.

---

## 다음 단계 (Case 2)

- **AI 내용 자동 생성 모드** — 기존 설명회 PPTX/Notion/PDF를 분석해 슬라이드 스크립트를 자동 생성.
- **추가 슬라이드 타입** — 연사 프로필 카드, 합격 사례 카드, 데이터 표(차트 포함) 등.
