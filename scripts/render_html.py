"""
JSON → HTML 슬라이드 렌더러.
Case 1 디자인 자동화 모드의 미리보기/PDF용 출력을 만든다.
- 각 슬라이드 타입(cover, chapter_divider, content, card_grid_4, stage_flow, alert_close)을
  하나의 HTML 파일로 이어 붙인다 (1920×1080 캔버스).
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
    """HTML escape, but preserve <em> and <b> from authoring."""
    if s is None:
        return ""
    return str(s).replace("\n", "<br>")


def _footer(meta: dict, page_no: int, total: int) -> str:
    talk = _esc(meta.get("talk_title_in_footer", ""))
    return f'''
    <div class="footer">
      <div class="left"><span class="brand">ZEROBASE</span><span>·</span><span>{talk}</span></div>
      <div class="right">{page_no:02d} / {total:02d}</div>
    </div>'''


def render_cover(meta: dict, page_no: int, total: int) -> str:
    speaker = meta.get("speaker", {}) or {}
    bio_html = "".join(f"<li>{_esc(b)}</li>" for b in speaker.get("bio", []))
    return f'''
    <section class="slide cover">
      <div class="cover-kicker">{_esc(meta.get("event_label",""))}</div>
      <div class="cover-title">{_esc(meta.get("title",""))}<br><em>{_esc(meta.get("title_em",""))}</em></div>
      <div class="cover-sub">{_esc(meta.get("subtitle",""))}</div>
      <div class="cover-meta">
        <div class="speaker">
          <b>{_esc(speaker.get("name",""))}</b>
          <span>{_esc(speaker.get("title",""))}</span>
        </div>
        <div>{_esc(meta.get("date",""))} · {_esc(meta.get("session",""))}</div>
      </div>
    </section>'''


def render_chapter_divider(s: dict, meta: dict, page_no: int, total: int) -> str:
    return f'''
    <section class="slide chapter-divider">
      <div class="divider-num">{_esc(s.get("ch",""))}</div>
      <h1 class="divider-title">{_esc(s.get("title",""))}</h1>
      <p class="divider-sub">{_esc(s.get("sub",""))}</p>
      {_footer(meta, page_no, total)}
    </section>'''


def render_content(s: dict, meta: dict, page_no: int, total: int) -> str:
    bullets = ""
    if s.get("bullets"):
        bullets = "<ul class='bullets'>" + "".join(
            f"<li>{_esc(b)}</li>" for b in s["bullets"]
        ) + "</ul>"
    return f'''
    <section class="slide">
      <div class="chapter-tag small">{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title">{s.get("title","")}</h2>
      <p class="slide-lede">{_esc(s.get("lede",""))}</p>
      <div class="head-gap"></div>
      <div class="body">{bullets}</div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_card_grid_4(s: dict, meta: dict, page_no: int, total: int) -> str:
    cards_html = ""
    for c in s.get("cards", [])[:4]:
        items = "".join(f"<li>{_esc(it)}</li>" for it in c.get("items", []))
        cards_html += f'''
        <div class="card-pastel">
          <div class="num">{_esc(c.get("num",""))}</div>
          <div class="card-title">{_esc(c.get("title",""))}</div>
          <ul>{items}</ul>
        </div>'''
    return f'''
    <section class="slide">
      <div class="chapter-tag small">{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title">{s.get("title","")}</h2>
      <div class="head-gap"></div>
      <div class="body"><div class="card-grid-4">{cards_html}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_stage_flow(s: dict, meta: dict, page_no: int, total: int) -> str:
    steps = s.get("steps", [])
    hi = s.get("highlight_index", -1)
    parts = []
    for i, step in enumerate(steps):
        cls = "stage-step highlight" if i == hi else "stage-step"
        parts.append(f'''
          <div class="{cls}">
            <div class="step-num">{_esc(step.get("num",""))}</div>
            <div class="step-name">{_esc(step.get("name",""))}</div>
            <div class="step-desc">{_esc(step.get("desc",""))}</div>
          </div>''')
        if i < len(steps) - 1:
            parts.append('<div class="stage-arrow">→</div>')
    return f'''
    <section class="slide">
      <div class="chapter-tag small">{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title">{s.get("title","")}</h2>
      <div class="head-gap"></div>
      <div class="body"><div class="stage-row">{''.join(parts)}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


def render_alert_close(s: dict, meta: dict, page_no: int, total: int) -> str:
    return f'''
    <section class="slide">
      <div class="chapter-tag small">{_esc(s.get("chapter",""))}</div>
      <h2 class="slide-title">{s.get("title","")}</h2>
      <p class="slide-lede">{_esc(s.get("lede",""))}</p>
      <div class="head-gap"></div>
      <div class="body"><div class="alert-note">{s.get("alert","")}</div></div>
      {_footer(meta, page_no, total)}
    </section>'''


RENDERERS = {
    "cover":            lambda s, m, p, t: render_cover(m, p, t),
    "chapter_divider":  render_chapter_divider,
    "content":          render_content,
    "card_grid_4":      render_card_grid_4,
    "stage_flow":       render_stage_flow,
    "alert_close":      render_alert_close,
}


def render_deck(data: dict) -> str:
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
        wraps.append(
            f'<div class="slide-wrap" data-idx="{i}">{inner}</div>'
        )
    css = (DESIGN / "base.css").read_text(encoding="utf-8")
    title = _esc(meta.get("title", "ZeroBase Deck"))
    deck_title = _esc(meta.get("talk_title_in_footer", meta.get("title", "")))

    js = r"""
(function(){
  var SLIDE_W = 1920, SLIDE_H = 1080;
  var stage = document.getElementById('stage');
  var wraps = Array.prototype.slice.call(document.querySelectorAll('.slide-wrap'));
  var fill  = document.querySelector('.hud .fill');
  var pager = document.querySelector('.hud .pager');
  var help  = document.getElementById('help');
  var total = wraps.length;
  var idx = 0;

  // Initial slide from URL hash, e.g. #3
  var h = parseInt((location.hash || '').replace('#',''), 10);
  if (!isNaN(h) && h >= 1 && h <= total) idx = h - 1;

  function fit(){
    var vw = window.innerWidth, vh = window.innerHeight;
    var scaleW = vw / SLIDE_W, scaleH = vh / SLIDE_H;
    var scale = Math.min(scaleW, scaleH) * 0.94; // small breathing room
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

  // Keyboard nav
  document.addEventListener('keydown', function(e){
    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ' || e.key === 'Enter')      { e.preventDefault(); go(idx + 1); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp' || e.key === 'Backspace')                  { e.preventDefault(); go(idx - 1); }
    else if (e.key === 'Home')                                                                       { e.preventDefault(); go(0); }
    else if (e.key === 'End')                                                                        { e.preventDefault(); go(total - 1); }
    else if (e.key === 'f' || e.key === 'F')                                                          { toggleFullscreen(); }
    else if (e.key === 'Escape')                                                                      { if (document.fullscreenElement) document.exitFullscreen(); }
  });

  function toggleFullscreen(){
    if (!document.fullscreenElement) document.documentElement.requestFullscreen();
    else document.exitFullscreen();
  }

  // Click zones
  document.getElementById('nav-prev').addEventListener('click', function(){ go(idx - 1); });
  document.getElementById('nav-next').addEventListener('click', function(){ go(idx + 1); });

  // Swipe (touch)
  var tx = 0;
  document.addEventListener('touchstart', function(e){ tx = e.touches[0].clientX; }, {passive: true});
  document.addEventListener('touchend',   function(e){
    var dx = e.changedTouches[0].clientX - tx;
    if (Math.abs(dx) > 40) go(idx + (dx < 0 ? 1 : -1));
  }, {passive: true});

  window.addEventListener('resize', fit);

  // Init
  fit(); go(idx);

  // Briefly show help
  if (help) {
    help.classList.add('show');
    setTimeout(function(){ help.classList.remove('show'); }, 3500);
  }
})();
"""
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

<div class="hud">
  <div class="bar"><div class="fill"></div></div>
  <div class="bottom">
    <span class="title">{deck_title}</span>
    <span class="pager">01 / {total:02d}</span>
  </div>
</div>

<div id="help" class="help">
  <kbd>←</kbd> <kbd>→</kbd> 이동 · <kbd>F</kbd> 풀스크린 · <kbd>Esc</kbd> 종료
</div>

<script>{js}</script>
</body></html>'''


def main():
    if len(sys.argv) < 2:
        print("usage: render_html.py <input.json> [output.html]", file=sys.stderr)
        sys.exit(2)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else OUTPUTS / (in_path.stem + ".html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    out_path.write_text(render_deck(data), encoding="utf-8")
    print(f"OK  HTML  -> {out_path}")


if __name__ == "__main__":
    main()
