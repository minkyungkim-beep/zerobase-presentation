"""
JSON → HTML 슬라이드 렌더러.
Case 1 디자인 자동화 모드의 미리보기/편집/PDF용 출력을 만든다.

특징:
- 1920×1080 캔버스, 풀스크린 슬라이드쇼 모드
- 모든 텍스트 필드에 data-edit 속성을 부여 → E키로 인라인 편집 모드 진입,
  변경 후 "💾 JSON 저장" 버튼으로 새 JSON 파일 다운로드.
- 외부 의존성 없음 (표준 라이브러리만 사용).
"""
from __future__ import annotations
import html
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "design_system"
OUTPUTS = ROOT / "outputs"


def _esc(s: Any) -> str:
    """HTML escape (간단판) — 줄바꿈만 <br>로. <em>/<b>는 보존."""
    if s is None:
        return ""
    return str(s).replace("\n", "<br>")


def _e(path: str, allow_html: bool = False) -> str:
    """data-edit 속성. allow_html=True면 innerHTML 보존(예: title의 <em>)."""
    h = ' data-edit-html="1"' if allow_html else ""
    return f' data-edit="{path}"{h}'


def _resolve_speaker_photo(sp: dict) -> str:
    """speaker.photo가 없으면 이름으로 assets/<name>*.{jpg,png} 자동 매칭.
    예: name="김준근" → assets/김준근 프로필.jpg, assets/김준근.png 등 자동 검색."""
    if sp.get("photo"):
        return sp["photo"]
    name = (sp.get("name") or "").strip()
    if not name:
        return ""
    asset_dir = ROOT / "assets"
    if not asset_dir.exists():
        return ""
    # 이름 변형 + 흔한 확장자 조합
    variants = [f"{name} 프로필", name, f"{name}_profile", f"{name}_프로필"]
    exts = ["jpg", "JPG", "jpeg", "JPEG", "png", "PNG"]
    for variant in variants:
        for ext in exts:
            cand = asset_dir / f"{variant}.{ext}"
            if cand.exists():
                return f"assets/{cand.name}"
    return ""


def _footer(meta: dict, page_no: int, total: int) -> str:
    talk = _esc(meta.get("talk_title_in_footer", ""))
    return f'''
    <div class="footer">
      <div class="left"><span class="brand">ZEROBASE</span><span>·</span><span{_e('meta.talk_title_in_footer')}>{talk}</span></div>
      <div class="right">{page_no:02d} / {total:02d}</div>
    </div>'''


def render_cover(meta: dict, page_no: int, total: int) -> str:
    speaker = meta.get("speaker", {}) or {}
    return f'''
    <section class="slide cover">
      <div class="cover-kicker"{_e('meta.event_label')}>{_esc(meta.get("event_label",""))}</div>
      <div class="cover-title">
        <span{_e('meta.title')}>{_esc(meta.get("title",""))}</span><br>
        <em{_e('meta.title_em')}>{_esc(meta.get("title_em",""))}</em>
      </div>
      <div class="cover-sub"{_e('meta.subtitle')}>{_esc(meta.get("subtitle",""))}</div>
      <div class="cover-meta">
        <div class="speaker">
          <b{_e('meta.speaker.name')}>{_esc(speaker.get("name",""))}</b>
          <span{_e('meta.speaker.title')}>{_esc(speaker.get("title",""))}</span>
        </div>
        <div><span{_e('meta.date')}>{_esc(meta.get("date",""))}</span> · <span{_e('meta.session')}>{_esc(meta.get("session",""))}</span></div>
      </div>
    </section>'''


def render_chapter_divider(s: dict, meta: dict, page_no: int, total: int) -> str:
    i = page_no - 1
    return f'''
    <section class="slide chapter-divider">
      <div class="divider-num"{_e(f'slides[{i}].ch')}>{_esc(s.get("ch",""))}</div>
      <h1 class="divider-title"{_e(f'slides[{i}].title', True)}>{_esc(s.get("title",""))}</h1>
      <p class="divider-sub"{_e(f'slides[{i}].sub')}>{_esc(s.get("sub",""))}</p>
      {_footer(meta, page_no, total)}
    </section>'''


def render_content(s: dict, meta: dict, page_no: int, total: int) -> str:
    i = page_no - 1
    bullets = ""
    if s.get("bullets"):
        lis = "".join(
            f'<li{_e(f"slides[{i}].bullets[{j}]")}>{_esc(b)}</li>'
            for j, b in enumerate(s["bullets"])
        )
        bullets = f"<ul class='bullets'>{lis}</ul>"
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      <p class="slide-lede"{_e(f'slides[{i}].lede')}>{_esc(s.get("lede",""))}</p>
      <div class="head-gap"></div>
      <div class="body body-top">{bullets}</div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_card_grid(s: dict, meta: dict, page_no: int, total: int) -> str:
    i = page_no - 1
    cards = s.get("cards", [])[:5]
    n = max(2, min(5, len(cards)))
    cards_html = ""
    for j, c in enumerate(cards):
        items = "".join(
            f'<li{_e(f"slides[{i}].cards[{j}].items[{k}]")}>{_esc(it)}</li>'
            for k, it in enumerate(c.get("items", []))
        )
        cards_html += f'''
        <div class="card-pastel">
          <div class="num"{_e(f'slides[{i}].cards[{j}].num')}>{_esc(c.get("num",""))}</div>
          <div class="card-title"{_e(f'slides[{i}].cards[{j}].title')}>{_esc(c.get("title",""))}</div>
          <ul>{items}</ul>
        </div>'''
    lede = (
        f'<p class="slide-lede"{_e(f"slides[{i}].lede")}>{_esc(s.get("lede",""))}</p>'
        if s.get("lede") else ""
    )
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      {lede}
      <div class="head-gap"></div>
      <div class="body"><div class="card-grid cols-{n}">{cards_html}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


# Backwards-compat alias
render_card_grid_4 = render_card_grid


def render_two_col(s: dict, meta: dict, page_no: int, total: int) -> str:
    i = page_no - 1
    cols = s.get("cols", [])[:2]
    cols_html = ""
    for j, col in enumerate(cols):
        items = "".join(
            f'<li{_e(f"slides[{i}].cols[{j}].items[{k}]")}>{_esc(it)}</li>'
            for k, it in enumerate(col.get("items", []))
        )
        accent = " accent" if col.get("accent") else ""
        num = (
            f'<div class="col-num"{_e(f"slides[{i}].cols[{j}].num")}>{_esc(col.get("num",""))}</div>'
            if col.get("num") else ""
        )
        lede = (
            f'<div class="col-lede"{_e(f"slides[{i}].cols[{j}].lede")}>{_esc(col.get("lede",""))}</div>'
            if col.get("lede") else ""
        )
        cols_html += f'''
        <div class="col{accent}">
          {num}
          <div class="col-title"{_e(f'slides[{i}].cols[{j}].title')}>{_esc(col.get("title",""))}</div>
          {lede}
          <ul>{items}</ul>
        </div>'''
    lede_top = (
        f'<p class="slide-lede"{_e(f"slides[{i}].lede")}>{_esc(s.get("lede",""))}</p>'
        if s.get("lede") else ""
    )
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      {lede_top}
      <div class="head-gap"></div>
      <div class="body"><div class="two-col">{cols_html}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_toc(s: dict, meta: dict, page_no: int, total: int) -> str:
    i = page_no - 1
    items = s.get("items", [])
    items_html = ""
    for k, it in enumerate(items):
        items_html += f'''
        <div class="toc-item">
          <span class="toc-num">{k+1:02d}</span>
          <span class="toc-text"{_e(f'slides[{i}].items[{k}]')}>{_esc(it)}</span>
        </div>'''
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter","Contents"))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","목차")}</h2>
      <div class="head-gap"></div>
      <div class="body"><div class="toc-grid">{items_html}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_speaker(s: dict, meta: dict, page_no: int, total: int) -> str:
    i = page_no - 1
    sp = s.get("speaker") or meta.get("speaker", {}) or {}
    # Speaker info comes from meta unless overridden in slide
    speaker_path_root = "meta.speaker" if not s.get("speaker") else f"slides[{i}].speaker"
    tags = "".join(
        f'<span class="speaker-tag"{_e(f"{speaker_path_root}.tags[{k}]")}>{_esc(t)}</span>'
        for k, t in enumerate(sp.get("tags", []))
    )
    bio = "".join(
        f'<li{_e(f"{speaker_path_root}.bio[{k}]")}>{_esc(b)}</li>'
        for k, b in enumerate(sp.get("bio", []))
    )
    photo_initial = (sp.get("name", "?")[:1])
    photo = sp.get("photo") or _resolve_speaker_photo(sp)
    if photo:
        photo_html = f'<div class="speaker-photo has-image"><img src="{html.escape(_img_src(photo))}" alt=""></div>'
    else:
        photo_html = f'<div class="speaker-photo">{_esc(photo_initial)}</div>'
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter","강사 소개"))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title')}>{_esc(s.get("title","오늘의 연사"))}</h2>
      <div class="head-gap"></div>
      <div class="body"><div class="speaker-card">
        {photo_html}
        <div class="speaker-info">
          <div class="speaker-name"{_e(f'{speaker_path_root}.name')}>{_esc(sp.get("name",""))}</div>
          <div class="speaker-title"{_e(f'{speaker_path_root}.title')}>{_esc(sp.get("title",""))}</div>
          <div class="speaker-tags">{tags}</div>
          <ul class="speaker-bio">{bio}</ul>
        </div>
      </div></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_qa_close(s: dict, meta: dict, page_no: int, total: int) -> str:
    i = page_no - 1
    contact = s.get("contact", "")
    thanks  = s.get("thanks", "")
    contact_html = (
        f'<div class="qa-contact"{_e(f"slides[{i}].contact")}>{_esc(contact)}</div>'
        if contact else ""
    )
    thanks_html = (
        f'<div class="qa-thanks"{_e(f"slides[{i}].thanks")}>{_esc(thanks)}</div>'
        if thanks else ""
    )
    return f'''
    <section class="slide" style="justify-content: center; align-items: center; text-align: center;">
      <div style="margin: auto;">
        <div class="qa-big">Q&amp;A</div>
        <div class="qa-sub"{_e(f'slides[{i}].sub')}>{_esc(s.get("sub",""))}</div>
        {contact_html}
        {thanks_html}
      </div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_compare_table(s: dict, meta: dict, page_no: int, total: int) -> str:
    i = page_no - 1
    headers = s.get("headers") or ["구분", "A", "B"]
    rows    = s.get("rows") or []
    accent_col = s.get("accent_col", -1)
    head_html = f'''
        <div class="compare-row head">
          <div{_e(f'slides[{i}].headers[0]')}>{_esc(headers[0])}</div>
          <div{_e(f'slides[{i}].headers[1]')}>{_esc(headers[1])}</div>
          <div{_e(f'slides[{i}].headers[2]')}>{_esc(headers[2])}</div>
        </div>'''
    rows_html = ""
    for ri, r in enumerate(rows):
        cells = r if isinstance(r, list) else [r.get("label",""), r.get("a",""), r.get("b","")]
        a_cls = "cell accent" if accent_col == 1 else "cell"
        b_cls = "cell accent" if accent_col == 2 else "cell"
        rows_html += f'''
        <div class="compare-row">
          <div class="label"{_e(f'slides[{i}].rows[{ri}][0]')}>{_esc(cells[0])}</div>
          <div class="{a_cls}"{_e(f'slides[{i}].rows[{ri}][1]')}>{_esc(cells[1])}</div>
          <div class="{b_cls}"{_e(f'slides[{i}].rows[{ri}][2]')}>{_esc(cells[2])}</div>
        </div>'''
    concl = ""
    if s.get("conclusion"):
        concl = f'<div class="compare-conclusion"{_e(f"slides[{i}].conclusion", True)}>{s["conclusion"]}</div>'
    lede = (
        f'<p class="slide-lede"{_e(f"slides[{i}].lede")}>{_esc(s.get("lede",""))}</p>'
        if s.get("lede") else ""
    )
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      {lede}
      <div class="head-gap"></div>
      <div class="body">
        <div class="compare-table">{head_html}{rows_html}</div>
        {concl}
      </div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_stage_flow(s: dict, meta: dict, page_no: int, total: int) -> str:
    i = page_no - 1
    steps = s.get("steps", [])
    hi = s.get("highlight_index", -1)
    parts = []
    for j, step in enumerate(steps):
        cls = "stage-step highlight" if j == hi else "stage-step"
        parts.append(f'''
          <div class="{cls}">
            <div class="step-num"{_e(f'slides[{i}].steps[{j}].num')}>{_esc(step.get("num",""))}</div>
            <div class="step-name"{_e(f'slides[{i}].steps[{j}].name')}>{_esc(step.get("name",""))}</div>
            <div class="step-desc"{_e(f'slides[{i}].steps[{j}].desc')}>{_esc(step.get("desc",""))}</div>
          </div>''')
        if j < len(steps) - 1:
            parts.append('<div class="stage-arrow">→</div>')
    lede = (
        f'<p class="slide-lede"{_e(f"slides[{i}].lede")}>{_esc(s.get("lede",""))}</p>'
        if s.get("lede") else ""
    )
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      {lede}
      <div class="head-gap"></div>
      <div class="body"><div class="stage-row">{''.join(parts)}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


# ===========================================================
#  Design system meta: color_palette / type_scale
# ===========================================================

def render_color_palette(s: dict, meta: dict, page_no: int, total: int) -> str:
    """N개 컬러 스와치 그리드. swatches[]는 {hex, name, role, token, on(텍스트색 hex 옵션)}."""
    i = page_no - 1
    swatches = s.get("swatches", [])
    n = max(3, min(5, s.get("cols", 4)))
    parts = []
    for j, sw in enumerate(swatches):
        hex_val = sw.get("hex", "#000000")
        name = sw.get("name", "")
        role = sw.get("role", "")
        token = sw.get("token", "")
        on = sw.get("on", "#ffffff")
        parts.append(f'''
        <div class="cp-swatch">
          <div class="cp-chip" style="background:{hex_val}; color:{on};"
               {_e(f"slides[{i}].swatches[{j}].name")}>{_esc(name)}</div>
          <div class="cp-body">
            <span class="role"{_e(f"slides[{i}].swatches[{j}].role")}>{_esc(role)}</span>
            <span class="hex"{_e(f"slides[{i}].swatches[{j}].hex")}>{_esc(hex_val)}</span>
            <span class="token"{_e(f"slides[{i}].swatches[{j}].token")}>{_esc(token)}</span>
          </div>
        </div>''')
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      <p class="slide-lede"{_e(f'slides[{i}].lede')}>{_esc(s.get("lede",""))}</p>
      <div class="head-gap"></div>
      <div class="body"><div class="cp-grid cols-{n}">{"".join(parts)}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_type_scale(s: dict, meta: dict, page_no: int, total: int) -> str:
    """타이포그래피 위계 테이블 — items[]는 {name, size_px, weight, leading, sample, color}."""
    i = page_no - 1
    items = s.get("items", [])
    rows = ""
    for j, it in enumerate(items):
        name = it.get("name", "")
        size_px = it.get("size_px", 18)
        weight = it.get("weight", 400)
        leading = it.get("leading", 1.4)
        tracking = it.get("tracking_em", 0)
        sample = it.get("sample", "샘플 텍스트")
        color = it.get("color", "var(--ink)")
        meta_text = f"font-size: {size_px}px<br>font-weight: {weight}<br>line-height: {leading}<br>letter-spacing: {tracking}em"
        sample_style = f"font-size:{size_px}px; font-weight:{weight}; line-height:{leading}; letter-spacing:{tracking}em; color:{color};"
        rows += f'''
        <div class="ts-row">
          <div class="ts-meta"><b{_e(f"slides[{i}].items[{j}].name")}>{_esc(name)}</b>{meta_text}</div>
          <div class="ts-sample"><span style="{sample_style}"{_e(f"slides[{i}].items[{j}].sample", True)}>{sample}</span></div>
        </div>'''
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      <p class="slide-lede"{_e(f'slides[{i}].lede')}>{_esc(s.get("lede",""))}</p>
      <div class="head-gap"></div>
      <div class="body"><div class="ts-table">{rows}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


# ===========================================================
#  6 new templates: checklist / summary_takeaway / dual_panel /
#  case_grid_4 / case_analysis / pipeline_matrix
# ===========================================================

def render_checklist(s: dict, meta: dict, page_no: int, total: int) -> str:
    """번호 리스트 + 외곽 박스. items 안 항목에 emphasis: True 주면 볼드+밑줄."""
    i = page_no - 1
    items = s.get("items", [])
    parts = []
    for k, it in enumerate(items):
        if isinstance(it, dict):
            text = it.get("text", "")
            cls = " class=\"emphasis\"" if it.get("emphasis") else ""
            parts.append(f'<li{cls}{_e(f"slides[{i}].items[{k}].text", True)}>{text}</li>')
        else:
            parts.append(f'<li{_e(f"slides[{i}].items[{k}]", True)}>{it}</li>')
    sub = (
        f'<p class="ck-sub"{_e(f"slides[{i}].subtitle")}>{_esc(s.get("subtitle",""))}</p>'
        if s.get("subtitle") else ""
    )
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      <div class="head-gap"></div>
      <div class="body"><div class="checklist-frame">
        <div class="ck-title"{_e(f'slides[{i}].box_title', True)}>{s.get("box_title","")}</div>
        {sub}
        <ol>{''.join(parts)}</ol>
      </div></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_summary_takeaway(s: dict, meta: dict, page_no: int, total: int) -> str:
    """3~4 카드 + 하단 takeaway 바. 표준 head 포맷(chapter + title + lede)."""
    i = page_no - 1
    cards = s.get("cards", [])[:4]
    n = max(2, min(4, len(cards)))
    cards_html = ""
    for j, c in enumerate(cards):
        items = "".join(
            f'<li{_e(f"slides[{i}].cards[{j}].items[{k}]", True)}>{it}</li>'
            for k, it in enumerate(c.get("items", []))
        )
        cards_html += f'''
        <div class="summary-card">
          <div class="head"{_e(f'slides[{i}].cards[{j}].title', True)}>{c.get("title","")}</div>
          <ul>{items}</ul>
        </div>'''
    # 호환: section_label이 있으면 chapter로, 없으면 chapter 사용
    chapter_text = s.get("chapter") or s.get("section_label", "")
    lede = (
        f'<p class="slide-lede"{_e(f"slides[{i}].lede")}>{_esc(s.get("lede",""))}</p>'
        if s.get("lede") else ""
    )
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(chapter_text)}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      {lede}
      <div class="head-gap"></div>
      <div class="body" style="gap: 18px;">
        <div class="summary-cards cols-{n}">{cards_html}</div>
        <div class="summary-takeaway"{_e(f'slides[{i}].takeaway', True)}>{s.get("takeaway","")}</div>
      </div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_dual_panel(s: dict, meta: dict, page_no: int, total: int) -> str:
    """좌(navy) / 우(red) 헤더 + 분할 패널. 각 패널은 여러 sub-section 가능."""
    i = page_no - 1
    def _pane(side: str, color: str, pane: dict) -> str:
        secs = pane.get("sections", [])
        sec_html = ""
        for si, sec in enumerate(secs):
            li_html = "".join(
                f'<li{_e(f"slides[{i}].{side}.sections[{si}].items[{k}]", True)}>{it}</li>'
                for k, it in enumerate(sec.get("items", []))
            )
            sec_html += f'''
            <div class="dp-section">
              <div class="sec-title {color}"{_e(f'slides[{i}].{side}.sections[{si}].title')}>{_esc(sec.get("title",""))}</div>
              <ul>{li_html}</ul>
            </div>'''
        foot = (
            f'<div class="dp-foot"{_e(f"slides[{i}].{side}.footnote")}>{_esc(pane.get("footnote",""))}</div>'
            if pane.get("footnote") else ""
        )
        tint_cls = "tint-blue" if color == "navy" else "tint-red"
        return f'''
        <div class="dp-pane {side}">
          <div class="dp-header {color}"{_e(f'slides[{i}].{side}.header')}>{_esc(pane.get("header",""))}</div>
          <div class="dp-body {tint_cls}">{sec_html}{foot}</div>
        </div>'''
    left  = _pane("left",  "navy", s.get("left", {}))
    right = _pane("right", "red",  s.get("right", {}))
    chapter_text = s.get("chapter") or s.get("section_label", "")
    lede = (
        f'<p class="slide-lede"{_e(f"slides[{i}].lede")}>{_esc(s.get("lede",""))}</p>'
        if s.get("lede") else ""
    )
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(chapter_text)}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      {lede}
      <div class="head-gap"></div>
      <div class="body">
        <div class="dp-grid">{left}{right}</div>
      </div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_case_grid_4(s: dict, meta: dict, page_no: int, total: int) -> str:
    """2x2 케이스 카드 — 좌상/우하 navy, 우상/좌하 red 교차. 각 카드 하단 → 결론."""
    i = page_no - 1
    cards = s.get("cards", [])[:4]
    parts = []
    for j, c in enumerate(cards):
        items = "".join(
            f'<li{_e(f"slides[{i}].cards[{j}].items[{k}]", True)}>{it}</li>'
            for k, it in enumerate(c.get("items", []))
        )
        arrow = (
            f'<div class="arrow"{_e(f"slides[{i}].cards[{j}].arrow", True)}>{c.get("arrow","")}</div>'
            if c.get("arrow") else ""
        )
        parts.append(f'''
        <div class="cell">
          <div class="ct"{_e(f'slides[{i}].cards[{j}].title', True)}>{c.get("title","")}</div>
          <ul>{items}</ul>
          {arrow}
        </div>''')
    chapter_text = s.get("chapter") or s.get("section_label", "")
    title_html = (
        f'<h2 class="slide-title"{_e(f"slides[{i}].title", True)}>{s.get("title","")}</h2>'
        if s.get("title") else ""
    )
    lede = (
        f'<p class="slide-lede"{_e(f"slides[{i}].lede")}>{_esc(s.get("lede",""))}</p>'
        if s.get("lede") else ""
    )
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(chapter_text)}</div>
      {title_html}
      {lede}
      <div class="head-gap"></div>
      <div class="body"><div class="cg4">{"".join(parts)}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_case_analysis(s: dict, meta: dict, page_no: int, total: int) -> str:
    """좌: 자료(이미지 또는 텍스트, mark 하이라이트 가능) / 우: 합격 포인트 N개 + 결론."""
    i = page_no - 1
    ref_inner = ""
    if s.get("ref_image"):
        ref_inner = f'<div class="ref-image"><img src="{html.escape(_img_src(s["ref_image"]))}" alt=""></div>'
    elif s.get("ref_text"):
        ref_inner = f'<div class="ref-text"{_e(f"slides[{i}].ref_text", True)}>{s["ref_text"]}</div>'
    findings = s.get("findings", [])
    pt_html = ""
    for j, f in enumerate(findings):
        pt_html += f'''
        <div class="ca-point">
          <div class="pt-label"{_e(f'slides[{i}].findings[{j}].label')}>{_esc(f.get("label",f"합격 포인트 {j+1}"))}</div>
          <div class="pt-text"{_e(f'slides[{i}].findings[{j}].text', True)}>{f.get("text","")}</div>
        </div>'''
    concl = (
        f'<div class="ca-conclusion"{_e(f"slides[{i}].conclusion", True)}>{s.get("conclusion","")}</div>'
        if s.get("conclusion") else ""
    )
    ref_title = (
        f'<div class="ref-title"{_e(f"slides[{i}].ref_title")}>{_esc(s.get("ref_title",""))}</div>'
        if s.get("ref_title") else ""
    )
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      <div class="head-gap"></div>
      <div class="body"><div class="ca-grid">
        <div class="ca-ref">{ref_title}{ref_inner}</div>
        <div class="ca-points">{pt_html}{concl}</div>
      </div></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_pipeline_matrix(s: dict, meta: dict, page_no: int, total: int) -> str:
    """3-stage horizontal 파이프라인. stages[].header + stages[].rows[][]."""
    i = page_no - 1
    stages = s.get("stages", [])[:3]
    while len(stages) < 3:
        stages.append({"header": "", "rows": []})
    # Header row
    head_row = '<div class="pm-row">'
    for si, stage in enumerate(stages):
        head_row += f'<div class="pm-cell"{_e(f"slides[{i}].stages[{si}].header")}>{_esc(stage.get("header",""))}</div>'
        if si < 2:
            head_row += '<div class="pm-arrow">→</div>'
    head_row += '</div>'
    # Body rows: take max(rows) per stage, pair them across stages
    max_rows = max((len(stage.get("rows", [])) for stage in stages), default=0)
    body_rows = ""
    for r in range(max_rows):
        row_html = '<div class="pm-row">'
        for si, stage in enumerate(stages):
            rows = stage.get("rows", [])
            cell = rows[r] if r < len(rows) else None
            if cell is None:
                row_html += '<div class="pm-cell empty"></div>'
            elif isinstance(cell, str):
                row_html += f'<div class="pm-cell"{_e(f"slides[{i}].stages[{si}].rows[{r}]")}>{_esc(cell)}</div>'
            elif isinstance(cell, list):
                # multiple parallel cells
                inner = "".join(
                    f'<div class="pm-cell"{_e(f"slides[{i}].stages[{si}].rows[{r}][{ci}]")}>{_esc(c) if isinstance(c,str) else _esc(c.get("label",""))}</div>'
                    for ci, c in enumerate(cell)
                )
                row_html += f'<div class="pm-cell empty" style="background:none; padding:0;"><div class="pm-cell-row" style="width:100%; grid-template-columns: repeat({len(cell)}, 1fr); display:grid; gap:6px;">{inner}</div></div>'
            elif isinstance(cell, dict):
                # dict with label and optional sub-cells
                if cell.get("sub"):
                    sub_inner = "".join(
                        f'<div class="pm-cell"{_e(f"slides[{i}].stages[{si}].rows[{r}].sub[{ci}]")}>{_esc(sc) if isinstance(sc,str) else _esc(sc.get("label",""))}</div>'
                        for ci, sc in enumerate(cell["sub"])
                    )
                    row_html += f'''<div style="display: grid; grid-template-rows: auto auto; gap: 4px;">
                      <div class="pm-cell"{_e(f"slides[{i}].stages[{si}].rows[{r}].label")}>{_esc(cell.get("label",""))}</div>
                      <div class="pm-sub-cells" style="grid-template-columns: repeat({len(cell["sub"])}, 1fr);">{sub_inner}</div>
                    </div>'''
                else:
                    row_html += f'<div class="pm-cell"{_e(f"slides[{i}].stages[{si}].rows[{r}].label")}>{_esc(cell.get("label",""))}</div>'
            if si < 2:
                row_html += '<div class="pm-arrow"></div>'
        row_html += '</div>'
        body_rows += row_html
    note = ""
    if s.get("note"):
        note_text = _esc(s["note"])
        note = f'<div class="pm-note"{_e(f"slides[{i}].note")}>{note_text}</div>'
    return f'''
    <section class="slide" style="position:relative;">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      <p class="slide-lede"{_e(f'slides[{i}].lede')}>{_esc(s.get("lede",""))}</p>
      <div class="head-gap"></div>
      <div class="body" style="position: relative;">
        <div>{head_row}{body_rows}</div>
        {note}
      </div>
      {_footer(meta, page_no, total)}
    </section>'''


def _img_src(path: str) -> str:
    """Resolve image path for HTML preview.
    Project assets/ folder is referenced via ../assets/ from outputs/."""
    if not path:
        return ""
    if path.startswith(("http://", "https://", "data:", "/")):
        return path
    # Relative to project root → from outputs/ go up one level
    return f"../{path}"


def render_image_full(s: dict, meta: dict, page_no: int, total: int) -> str:
    """Full-bleed image with optional caption below."""
    i = page_no - 1
    img = s.get("image", "")
    caption = s.get("caption", "")
    bg_cls = " bg-light" if s.get("bg") == "light" else ""
    caption_html = (
        f'<div class="image-caption"{_e(f"slides[{i}].caption", True)}>{caption}</div>'
        if caption else ""
    )
    return f'''
    <section class="slide image-full{bg_cls}">
      <div class="img-wrap"><img src="{html.escape(_img_src(img))}" alt=""></div>
      {caption_html}
      {_footer(meta, page_no, total)}
    </section>'''


def render_image_headed(s: dict, meta: dict, page_no: int, total: int) -> str:
    """Header (chapter + title + lede) + framed image below."""
    i = page_no - 1
    img = s.get("image", "")
    lede = (
        f'<p class="slide-lede"{_e(f"slides[{i}].lede")}>{_esc(s.get("lede",""))}</p>'
        if s.get("lede") else ""
    )
    return f'''
    <section class="slide image-headed">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      {lede}
      <div class="img-zone"><img src="{html.escape(_img_src(img))}" alt=""></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_image_split(s: dict, meta: dict, page_no: int, total: int) -> str:
    """Image on one side, text content on the other."""
    i = page_no - 1
    img = s.get("image", "")
    pos = s.get("image_position", "left")  # "left" or "right"
    items = "".join(
        f'<li{_e(f"slides[{i}].items[{k}]")}>{_esc(it)}</li>'
        for k, it in enumerate(s.get("items", []))
    )
    items_html = f"<ul>{items}</ul>" if items else ""
    body_title = (
        f'<h3{_e(f"slides[{i}].body_title", True)}>{s.get("body_title","")}</h3>'
        if s.get("body_title") else ""
    )
    body_lede = (
        f'<div class="lede"{_e(f"slides[{i}].body_lede")}>{_esc(s.get("body_lede",""))}</div>'
        if s.get("body_lede") else ""
    )
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      <div class="head-gap"></div>
      <div class="body"><div class="image-split {pos}">
        <div class="img-pane"><img src="{html.escape(_img_src(img))}" alt=""></div>
        <div class="text-pane">{body_title}{body_lede}{items_html}</div>
      </div></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_alert_close(s: dict, meta: dict, page_no: int, total: int) -> str:
    i = page_no - 1
    return f'''
    <section class="slide">
      <div class="chapter-tag small"{_e(f'slides[{i}].chapter')}>{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title"{_e(f'slides[{i}].title', True)}>{s.get("title","")}</h2>
      <p class="slide-lede"{_e(f'slides[{i}].lede')}>{_esc(s.get("lede",""))}</p>
      <div class="head-gap"></div>
      <div class="body body-center"><div class="alert-note"{_e(f'slides[{i}].alert', True)}>{s.get("alert","")}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


RENDERERS = {
    "cover":            lambda s, m, p, t: render_cover(m, p, t),
    "chapter_divider":  render_chapter_divider,
    "content":          render_content,
    "card_grid_4":      render_card_grid_4,
    "card_grid":        render_card_grid,
    "two_col":          render_two_col,
    "toc":              render_toc,
    "speaker":          render_speaker,
    "stage_flow":       render_stage_flow,
    "alert_close":      render_alert_close,
    "qa_close":         render_qa_close,
    "compare_table":    render_compare_table,
    "image_full":       render_image_full,
    "image_headed":     render_image_headed,
    "image_split":      render_image_split,
    "checklist":        render_checklist,
    "summary_takeaway": render_summary_takeaway,
    "dual_panel":       render_dual_panel,
    "case_grid_4":      render_case_grid_4,
    "case_analysis":    render_case_analysis,
    "pipeline_matrix":  render_pipeline_matrix,
    "color_palette":    render_color_palette,
    "type_scale":       render_type_scale,
}


VIEWER_JS = r"""
(function(){
  var SLIDE_W = 1920, SLIDE_H = 1080;
  var stage = document.getElementById('stage');
  var wraps = Array.prototype.slice.call(document.querySelectorAll('.slide-wrap'));
  var fill  = document.querySelector('.hud .fill');
  var pager = document.querySelector('.hud .pager');
  var help  = document.getElementById('help');
  var total = wraps.length;
  var idx = 0;
  var editMode = false;

  // Initial slide from URL hash, e.g. #3
  var h = parseInt((location.hash || '').replace('#',''), 10);
  if (!isNaN(h) && h >= 1 && h <= total) idx = h - 1;

  function fit(){
    var vw = window.innerWidth, vh = window.innerHeight;
    var scaleW = vw / SLIDE_W, scaleH = vh / SLIDE_H;
    var scale = Math.min(scaleW, scaleH) * 0.94;
    var w = SLIDE_W * scale, hh = SLIDE_H * scale;
    stage.style.width  = w + 'px';
    stage.style.height = hh + 'px';
    wraps.forEach(function(wr){
      var s = wr.querySelector('.slide');
      if(s) s.style.transform = 'scale(' + scale + ')';
    });
  }

  function go(n){
    idx = Math.max(0, Math.min(total - 1, n));
    wraps.forEach(function(wr, i){
      wr.classList.toggle('is-active', i === idx);
    });
    if (fill)  fill.style.width = ((idx + 1) / total * 100) + '%';
    if (pager) pager.textContent = String(idx + 1).padStart(2,'0') + ' / ' + String(total).padStart(2,'0');
    history.replaceState(null, '', '#' + (idx + 1));
  }

  // ---------- Edit mode ----------
  function toggleEdit(){
    editMode = !editMode;
    document.body.classList.toggle('edit-mode', editMode);
    document.querySelectorAll('[data-edit]').forEach(function(el){
      if (editMode) el.setAttribute('contenteditable', 'true');
      else el.removeAttribute('contenteditable');
    });
    var btn = document.getElementById('edit-btn');
    if (btn) btn.textContent = editMode ? '편집 끝내기 (E)' : '✏️ 편집 (E)';
    var bar = document.getElementById('edit-bar');
    if (bar) bar.classList.toggle('show', editMode);
  }

  function getPathSafe(obj, parts){
    var cur = obj;
    for (var i = 0; i < parts.length; i++){
      if (cur == null) return undefined;
      cur = cur[parts[i]];
    }
    return cur;
  }
  function setPath(obj, path, value){
    var parts = path.replace(/\[(\d+)\]/g, '.$1').split('.').filter(Boolean);
    var cur = obj;
    for (var i = 0; i < parts.length - 1; i++){
      var k = parts[i];
      // numeric index
      if (/^\d+$/.test(k)) k = parseInt(k, 10);
      if (cur[k] == null){
        // create container
        var nextK = parts[i+1];
        cur[k] = (/^\d+$/.test(nextK)) ? [] : {};
      }
      cur = cur[k];
    }
    var lastK = parts[parts.length - 1];
    if (/^\d+$/.test(lastK)) lastK = parseInt(lastK, 10);
    cur[lastK] = value;
  }

  function buildEditedJSON(){
    var srcEl = document.getElementById('deck-source');
    var src = JSON.parse(srcEl.textContent);
    document.querySelectorAll('[data-edit]').forEach(function(el){
      var path = el.getAttribute('data-edit');
      var asHtml = el.getAttribute('data-edit-html') === '1';
      var value;
      if (asHtml){
        value = el.innerHTML.trim()
                  .replace(/<br\s*\/?>/gi, '\n')
                  .replace(/&nbsp;/g, ' ');
      } else {
        value = el.textContent.trim();
      }
      setPath(src, path, value);
    });
    return src;
  }

  function downloadJSON(){
    var data = buildEditedJSON();
    var name = (document.getElementById('deck-source').getAttribute('data-name') || 'edited') + '.json';
    var blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(function(){ URL.revokeObjectURL(url); a.remove(); }, 100);
    var msg = document.getElementById('toast');
    if (msg){ msg.textContent = '저장됨: ' + name; msg.classList.add('show');
      setTimeout(function(){ msg.classList.remove('show'); }, 2500); }
  }

  function resetEdits(){
    if (!confirm('모든 편집을 원래대로 되돌릴까요?')) return;
    var src = JSON.parse(document.getElementById('deck-source').textContent);
    document.querySelectorAll('[data-edit]').forEach(function(el){
      var path = el.getAttribute('data-edit');
      var asHtml = el.getAttribute('data-edit-html') === '1';
      var parts = path.replace(/\[(\d+)\]/g, '.$1').split('.').filter(Boolean);
      var v = getPathSafe(src, parts.map(function(p){return /^\d+$/.test(p)?parseInt(p,10):p;}));
      if (v == null) return;
      if (asHtml) el.innerHTML = String(v).replace(/\n/g,'<br>');
      else el.textContent = String(v);
    });
  }

  // ---------- Keyboard ----------
  document.addEventListener('keydown', function(e){
    // If typing inside an editable element, don't navigate
    var t = e.target;
    var typing = t && t.isContentEditable;
    if (typing){
      // Allow Esc to exit edit on element
      if (e.key === 'Escape') t.blur();
      return;
    }
    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ' || e.key === 'Enter')   { e.preventDefault(); go(idx + 1); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp' || e.key === 'Backspace')              { e.preventDefault(); go(idx - 1); }
    else if (e.key === 'Home')                                                                   { e.preventDefault(); go(0); }
    else if (e.key === 'End')                                                                    { e.preventDefault(); go(total - 1); }
    else if (e.key === 'f' || e.key === 'F')                                                      { toggleFullscreen(); }
    else if (e.key === 'e' || e.key === 'E')                                                      { e.preventDefault(); toggleEdit(); }
    else if (e.key === 'Escape')                                                                  { if (document.fullscreenElement) document.exitFullscreen(); }
  });

  function toggleFullscreen(){
    if (!document.fullscreenElement) document.documentElement.requestFullscreen();
    else document.exitFullscreen();
  }

  // ---------- Click zones ----------
  document.getElementById('nav-prev').addEventListener('click', function(){ if(!editMode) go(idx - 1); });
  document.getElementById('nav-next').addEventListener('click', function(){ if(!editMode) go(idx + 1); });

  // ---------- Edit bar buttons ----------
  var btnEdit  = document.getElementById('edit-btn');
  var btnSave  = document.getElementById('save-btn');
  var btnReset = document.getElementById('reset-btn');
  if (btnEdit)  btnEdit.addEventListener('click', toggleEdit);
  if (btnSave)  btnSave.addEventListener('click', downloadJSON);
  if (btnReset) btnReset.addEventListener('click', resetEdits);

  // ---------- Touch swipe ----------
  var tx = 0;
  document.addEventListener('touchstart', function(e){ tx = e.touches[0].clientX; }, {passive: true});
  document.addEventListener('touchend',   function(e){
    if (editMode) return;
    var dx = e.changedTouches[0].clientX - tx;
    if (Math.abs(dx) > 40) go(idx + (dx < 0 ? 1 : -1));
  }, {passive: true});

  window.addEventListener('resize', fit);

  // Init
  fit(); go(idx);

  if (help) {
    help.classList.add('show');
    setTimeout(function(){ help.classList.remove('show'); }, 4000);
  }
})();
"""


PRINT_CSS = """
/* ===== Print mode (Cmd+P → PDF로 저장) ===== */
@media print {
  html, body { background: #fff !important; height: auto !important; overflow: visible !important; }
  .viewer { position: static !important; display: block !important; }
  .stage { box-shadow: none !important; width: 1920px !important; height: auto !important; }
  .slide-wrap {
    position: relative !important;
    inset: auto !important;
    opacity: 1 !important; visibility: visible !important;
    width: 1920px !important; height: 1080px !important;
    page-break-after: always; break-after: page;
    display: block !important;
  }
  .slide-wrap:last-child { page-break-after: auto; }
  .slide {
    position: absolute !important; top: 0 !important; left: 0 !important;
    transform: none !important;
  }
  .nav-zone, .hud, #help, #edit-toggle, #edit-bar, #toast { display: none !important; }
  @page { size: 1920px 1080px; margin: 0; }
}
"""

EDIT_CSS = """
/* ----- Edit mode styling ----- */
body.edit-mode [data-edit] {
  outline: 1px dashed transparent;
  outline-offset: 2px;
  transition: outline-color 0.12s ease;
  cursor: text;
}
body.edit-mode [data-edit]:hover { outline-color: rgba(28,40,133,0.45); }
body.edit-mode [data-edit]:focus {
  outline: 2px solid #1c2885;
  background: rgba(234,241,251,0.45);
}
body.edit-mode .nav-zone { display: none !important; }

#edit-bar {
  position: fixed; top: 16px; left: 50%; transform: translateX(-50%);
  z-index: 14;
  display: none; gap: 8px; padding: 8px;
  background: rgba(255,255,255,0.96);
  border: 1px solid rgba(28,40,133,0.18);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.18);
  font-size: 13px;
}
#edit-bar.show { display: flex; }
#edit-bar button {
  font-family: inherit; font-size: 12px; font-weight: 600;
  padding: 8px 14px; border: 1px solid rgba(28,40,133,0.2);
  background: #fff; color: #0e1430; cursor: pointer;
  letter-spacing: -0.005em;
}
#edit-bar button:hover { background: #f2f3f8; }
#edit-bar button.primary { background: #1c2885; color: #fff; border-color: #1c2885; }
#edit-bar button.primary:hover { background: #0e1430; }
#edit-bar .hint { font-size: 11px; color: #737991; padding: 0 8px; align-self: center; }

#edit-toggle {
  position: fixed; top: 16px; left: 16px; z-index: 13;
  font-family: inherit; font-size: 12px; font-weight: 600;
  padding: 8px 14px;
  background: rgba(255,255,255,0.94); color: #0e1430;
  border: 1px solid rgba(28,40,133,0.18); border-radius: 4px;
  cursor: pointer; letter-spacing: -0.005em;
}
#edit-toggle:hover { background: #fff; }

#toast {
  position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%);
  background: #0e8a4f; color: #fff;
  padding: 10px 20px; font-size: 13px; font-weight: 600;
  border-radius: 4px; opacity: 0; pointer-events: none;
  transition: opacity 0.2s ease;
  z-index: 15; letter-spacing: -0.005em;
}
#toast.show { opacity: 1; }
"""


def render_deck(data: dict, source_name: str = "deck") -> str:
    meta = data.get("meta", {})
    slides = data.get("slides", [])
    total = len(slides)
    wraps = []
    for i, s in enumerate(slides, 1):
        kind = s.get("type")
        fn = RENDERERS.get(kind)
        if not fn:
            inner = f'<section class="slide"><h2>Unknown slide type: {_esc(kind)}</h2></section>'
        else:
            inner = fn(s, meta, i, total)
        wraps.append(f'<div class="slide-wrap" data-idx="{i}">{inner}</div>')

    css = (DESIGN / "base.css").read_text(encoding="utf-8") + EDIT_CSS + PRINT_CSS
    title = _esc(meta.get("title", "ZeroBase Deck"))
    deck_title = _esc(meta.get("talk_title_in_footer", meta.get("title", "")))

    # Embed source for resetEdits + filename hint
    source_json = html.escape(json.dumps(data, ensure_ascii=False))

    return f'''<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8">
<title>{title}</title>
<style>{css}</style>
</head><body>
<div class="viewer">
  <div id="stage" class="stage">
    {"".join(wraps)}
  </div>
</div>

<div id="nav-prev" class="nav-zone prev" title="이전"><div class="arrow">‹</div></div>
<div id="nav-next" class="nav-zone next" title="다음"><div class="arrow">›</div></div>

<button id="edit-toggle" type="button" onclick="document.getElementById('edit-btn').click()">✏️ 편집 (E)</button>

<div id="edit-bar">
  <button id="edit-btn" type="button">편집 끝내기 (E)</button>
  <button id="save-btn" type="button" class="primary">💾 JSON 저장</button>
  <button id="reset-btn" type="button">↺ 되돌리기</button>
  <span class="hint">텍스트 클릭 → 수정 → JSON 저장</span>
</div>

<div class="hud">
  <div class="bar"><div class="fill"></div></div>
  <div class="bottom">
    <span class="title">{deck_title}</span>
    <span class="pager">01 / {total:02d}</span>
  </div>
</div>

<div id="help" class="help">
  <kbd>←</kbd> <kbd>→</kbd> 이동 · <kbd>F</kbd> 풀스크린 · <kbd>E</kbd> 편집 모드 · <kbd>Esc</kbd> 종료
</div>

<div id="toast"></div>

<script type="application/json" id="deck-source" data-name="{source_name}">{source_json}</script>
<script>{VIEWER_JS}</script>
</body></html>'''


def main():
    if len(sys.argv) < 2:
        print("usage: render_html.py <input.json> [output.html]", file=sys.stderr)
        sys.exit(2)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else OUTPUTS / (in_path.stem + ".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    out_path.write_text(render_deck(data, source_name=in_path.stem), encoding="utf-8")
    print(f"OK  HTML  -> {out_path}")


if __name__ == "__main__":
    main()
