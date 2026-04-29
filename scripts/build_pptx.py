"""
JSON → 편집 가능한 PPTX 생성기.
- 슬라이드 캔버스: 13.333 × 7.5 inch (16:9, 1920×1080 매핑)
- 디자인 토큰은 design_system/tokens.json 단일 소스에서 가져옴
- 타입별 슬라이드 빌더: cover / chapter_divider / content / card_grid_4 / stage_flow / alert_close
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree


ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "design_system"
OUTPUTS = ROOT / "outputs"

SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5
EDGE_IN    = 0.7    # 100 px @ 1920 ≈ 0.7 inch
TOP_IN     = 0.65

FONT_FAMILY = "Pretendard Variable"
FONT_FALLBACK = "Pretendard"
FONT_SAFE = "Apple SD Gothic Neo"  # macOS fallback


# ---------- Token loading ----------

with open(DESIGN / "tokens.json", encoding="utf-8") as f:
    TOKENS = json.load(f)
COLORS = TOKENS["colors"]
TYPE   = TOKENS["type"]


def hex_to_rgb(h: str) -> RGBColor:
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def C(name: str) -> RGBColor:
    return hex_to_rgb(COLORS[name])


# ---------- Inline markup parser ----------

INLINE_RE = re.compile(r"(<em>.*?</em>|<b>.*?</b>)", re.DOTALL)
TAG_RE    = re.compile(r"<(em|b)>(.*?)</\1>", re.DOTALL)


def parse_inline(text: str):
    """Split text into runs: [(text, {"em":bool,"b":bool}), ...]
    Supports <em> (accent color) and <b> (bold). Newlines preserved."""
    if text is None:
        return [("", {})]
    parts = INLINE_RE.split(text)
    runs = []
    for p in parts:
        if not p:
            continue
        m = TAG_RE.match(p)
        if m:
            tag, inner = m.group(1), m.group(2)
            attrs = {"em": tag == "em", "b": tag == "b"}
            runs.append((inner, attrs))
        else:
            runs.append((p, {}))
    return runs


# ---------- Low-level drawing helpers ----------

def add_text(slide, x, y, w, h, text, *, size_pt, weight=400, color="ink",
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, leading=1.3,
             tracking_em=0, allow_inline=True):
    """Add a text box with given style. Supports <em>/<b> inline markup."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    # Handle multi-line: split by \n
    lines = str(text).split("\n")
    for li, line in enumerate(lines):
        p = tf.paragraphs[0] if li == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = leading
        # Clear any existing runs from default empty paragraph
        for old_r in list(p.runs):
            old_r._r.getparent().remove(old_r._r)
        runs = parse_inline(line) if allow_inline else [(line, {})]
        for j, (txt, attrs) in enumerate(runs):
            r = p.add_run()
            r.text = txt
            r.font.name = FONT_FAMILY
            r.font.size = Pt(size_pt)
            r.font.bold = (weight >= 700) or attrs.get("b", False)
            run_color = "accent" if attrs.get("em") else color
            r.font.color.rgb = C(run_color)
            # tracking via XML <a:rPr spc="-N"> (1/100 pt)
            if tracking_em:
                spc = int(tracking_em * size_pt * 100)
                rPr = r._r.get_or_add_rPr()
                rPr.set("spc", str(spc))
    return tb


def add_rect(slide, x, y, w, h, *, fill="paper", line=None, line_w_pt=0.75):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                 Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = C(fill)
    if line:
        shp.line.color.rgb = C(line)
        shp.line.width = Pt(line_w_pt)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def add_hline(slide, x, y, w, *, color="line", weight_pt=0.75):
    ln = slide.shapes.add_connector(1, Inches(x), Inches(y), Inches(x + w), Inches(y))
    ln.line.color.rgb = C(color)
    ln.line.width = Pt(weight_pt)
    return ln


def add_footer(slide, meta, page_no, total):
    talk = meta.get("talk_title_in_footer", "")
    add_hline(slide, EDGE_IN, SLIDE_H_IN - 0.55, SLIDE_W_IN - 2 * EDGE_IN, color="line")
    add_text(slide, EDGE_IN, SLIDE_H_IN - 0.5, 9, 0.3,
             "ZEROBASE", size_pt=10, weight=700, color="ink",
             tracking_em=-0.01, allow_inline=False)
    add_text(slide, EDGE_IN + 1.0, SLIDE_H_IN - 0.5, 9, 0.3,
             f"·  {talk}", size_pt=10, weight=400, color="muted",
             allow_inline=False)
    add_text(slide, SLIDE_W_IN - EDGE_IN - 1.5, SLIDE_H_IN - 0.5, 1.5, 0.3,
             f"{page_no:02d} / {total:02d}", size_pt=10, weight=500,
             color="muted", align=PP_ALIGN.RIGHT, allow_inline=False)


def add_chapter_tag(slide, x, y, text, small=False):
    sz = 14 if small else 18
    return add_text(slide, x, y, SLIDE_W_IN - 2 * EDGE_IN, 0.45,
                    text, size_pt=sz, weight=700, color="accent",
                    tracking_em=-0.01, allow_inline=False)


# ---------- Slide builders ----------

def slide_cover(prs, meta):
    blank = prs.slide_layouts[6]
    s = prs.slides.add_slide(blank)
    add_text(s, EDGE_IN + 0.2, 1.4, SLIDE_W_IN - 2 * EDGE_IN, 0.5,
             meta.get("event_label", ""),
             size_pt=14, weight=700, color="accent",
             tracking_em=0.18, allow_inline=False)
    title_text = meta.get("title", "")
    em_text = meta.get("title_em", "")
    add_text(s, EDGE_IN + 0.2, 2.1, SLIDE_W_IN - 2 * EDGE_IN, 1.3,
             title_text, size_pt=56, weight=800, color="ink",
             tracking_em=-0.02, leading=1.05, allow_inline=False)
    if em_text:
        add_text(s, EDGE_IN + 0.2, 3.3, SLIDE_W_IN - 2 * EDGE_IN, 1.3,
                 em_text, size_pt=56, weight=800, color="accent",
                 tracking_em=-0.02, leading=1.05, allow_inline=False)
    add_text(s, EDGE_IN + 0.2, 4.7, SLIDE_W_IN - 2 * EDGE_IN, 1.4,
             meta.get("subtitle", ""), size_pt=20, weight=500,
             color="muted_2", leading=1.4, allow_inline=False)
    # bottom meta band
    add_hline(s, EDGE_IN + 0.2, SLIDE_H_IN - 1.2, SLIDE_W_IN - 2 * (EDGE_IN + 0.2),
              color="line")
    sp = meta.get("speaker", {}) or {}
    add_text(s, EDGE_IN + 0.2, SLIDE_H_IN - 1.05, 7, 0.4,
             sp.get("name", ""), size_pt=18, weight=700, color="ink",
             allow_inline=False)
    add_text(s, EDGE_IN + 0.2, SLIDE_H_IN - 0.65, 9, 0.35,
             sp.get("title", ""), size_pt=12, weight=500, color="muted_2",
             allow_inline=False)
    add_text(s, SLIDE_W_IN - EDGE_IN - 4.2, SLIDE_H_IN - 1.05, 4, 0.4,
             f"{meta.get('date','')}  ·  {meta.get('session','')}",
             size_pt=14, weight=500, color="muted_2", align=PP_ALIGN.RIGHT,
             allow_inline=False)


def slide_chapter_divider(prs, meta, s_data, page_no, total):
    blank = prs.slide_layouts[6]
    s = prs.slides.add_slide(blank)
    bg = add_rect(s, 0, 0, SLIDE_W_IN, SLIDE_H_IN, fill="paper_2")
    bg.shadow.inherit = False
    add_text(s, EDGE_IN + 0.4, 1.6, SLIDE_W_IN - 2 * EDGE_IN, 0.5,
             s_data.get("ch", ""), size_pt=18, weight=700,
             color="accent", tracking_em=0.2, allow_inline=False)
    add_text(s, EDGE_IN + 0.4, 2.3, SLIDE_W_IN - 2 * EDGE_IN, 3.0,
             s_data.get("title", ""), size_pt=72, weight=800,
             color="ink", tracking_em=-0.02, leading=1.05,
             allow_inline=False)
    if s_data.get("sub"):
        add_text(s, EDGE_IN + 0.4, 5.4, SLIDE_W_IN - 2 * EDGE_IN, 1.0,
                 s_data["sub"], size_pt=18, weight=500, color="muted_2",
                 leading=1.45, allow_inline=False)
    add_footer(s, meta, page_no, total)


def slide_content(prs, meta, s_data, page_no, total):
    blank = prs.slide_layouts[6]
    s = prs.slides.add_slide(blank)
    add_chapter_tag(s, EDGE_IN, TOP_IN, s_data.get("chapter", ""), small=True)
    add_text(s, EDGE_IN, TOP_IN + 0.4, SLIDE_W_IN - 2 * EDGE_IN, 1.6,
             s_data.get("title", ""), size_pt=40, weight=800,
             color="ink", tracking_em=-0.02, leading=1.08)
    add_text(s, EDGE_IN, TOP_IN + 1.95, SLIDE_W_IN - 2 * EDGE_IN, 0.9,
             s_data.get("lede", ""), size_pt=18, weight=500,
             color="muted_2", leading=1.45, allow_inline=False)
    # bullets
    bullets = s_data.get("bullets") or []
    by = TOP_IN + 3.1
    for b in bullets:
        # bullet mark
        bx = EDGE_IN + 0.05
        bm = add_rect(s, bx, by + 0.18, 0.18, 0.03, fill="accent")
        bm.line.fill.background()
        add_text(s, bx + 0.32, by, SLIDE_W_IN - 2 * EDGE_IN - 0.4, 0.6,
                 b, size_pt=18, weight=400, color="ink", leading=1.5,
                 allow_inline=False)
        by += 0.55
    add_footer(s, meta, page_no, total)


def slide_card_grid_4(prs, meta, s_data, page_no, total):
    blank = prs.slide_layouts[6]
    s = prs.slides.add_slide(blank)
    add_chapter_tag(s, EDGE_IN, TOP_IN, s_data.get("chapter", ""), small=True)
    add_text(s, EDGE_IN, TOP_IN + 0.4, SLIDE_W_IN - 2 * EDGE_IN, 1.6,
             s_data.get("title", ""), size_pt=36, weight=800,
             color="ink", tracking_em=-0.02, leading=1.08)
    cards = (s_data.get("cards") or [])[:4]
    n = max(1, len(cards))
    inner_gap = 0.18
    available = SLIDE_W_IN - 2 * EDGE_IN
    card_w = (available - inner_gap * (n - 1)) / n
    card_h = 3.6
    cy = TOP_IN + 2.5
    for i, c in enumerate(cards):
        cx = EDGE_IN + i * (card_w + inner_gap)
        bg = add_rect(s, cx, cy, card_w, card_h, fill="pastel_blue")
        bg.line.fill.background()
        # number
        add_text(s, cx + 0.25, cy + 0.25, card_w - 0.5, 0.35,
                 c.get("num", ""), size_pt=11, weight=700, color="accent",
                 tracking_em=0.16, allow_inline=False)
        # title
        add_text(s, cx + 0.25, cy + 0.6, card_w - 0.5, 0.95,
                 c.get("title", ""), size_pt=20, weight=700, color="ink",
                 leading=1.25, allow_inline=False)
        # underline
        add_hline(s, cx + 0.25, cy + 1.6, card_w - 0.5, color="line", weight_pt=0.75)
        # items
        iy = cy + 1.75
        for it in (c.get("items") or [])[:5]:
            # mark
            mark = add_rect(s, cx + 0.28, iy + 0.13, 0.13, 0.025, fill="accent")
            mark.line.fill.background()
            add_text(s, cx + 0.5, iy, card_w - 0.7, 0.5,
                     it, size_pt=13, weight=400, color="muted_2",
                     leading=1.45, allow_inline=False)
            iy += 0.42
    add_footer(s, meta, page_no, total)


def slide_stage_flow(prs, meta, s_data, page_no, total):
    blank = prs.slide_layouts[6]
    s = prs.slides.add_slide(blank)
    add_chapter_tag(s, EDGE_IN, TOP_IN, s_data.get("chapter", ""), small=True)
    add_text(s, EDGE_IN, TOP_IN + 0.4, SLIDE_W_IN - 2 * EDGE_IN, 1.6,
             s_data.get("title", ""), size_pt=40, weight=800,
             color="ink", tracking_em=-0.02, leading=1.08)
    steps = s_data.get("steps") or []
    hi = s_data.get("highlight_index", -1)
    n = max(1, len(steps))
    arrow_w = 0.45
    inner_gap = 0.0
    available = SLIDE_W_IN - 2 * EDGE_IN
    box_w = (available - arrow_w * (n - 1)) / n
    box_h = 2.2
    by = TOP_IN + 3.3
    for i, st in enumerate(steps):
        x = EDGE_IN + i * (box_w + arrow_w)
        is_hi = (i == hi)
        bg = add_rect(s, x, by, box_w, box_h,
                      fill=("ink_2" if is_hi else "paper"),
                      line=(None if is_hi else "line"),
                      line_w_pt=0.75)
        if is_hi:
            bg.line.fill.background()
        add_text(s, x + 0.3, by + 0.3, box_w - 0.6, 0.4,
                 st.get("num", ""), size_pt=11, weight=700,
                 color=("paper" if is_hi else "accent"),
                 tracking_em=0.18, allow_inline=False)
        add_text(s, x + 0.3, by + 0.7, box_w - 0.6, 0.7,
                 st.get("name", ""), size_pt=22, weight=700,
                 color=("paper" if is_hi else "ink"),
                 tracking_em=-0.01, allow_inline=False)
        add_text(s, x + 0.3, by + 1.45, box_w - 0.6, 0.7,
                 st.get("desc", ""), size_pt=13, weight=400,
                 color=("paper" if is_hi else "muted_2"),
                 leading=1.4, allow_inline=False)
        if i < len(steps) - 1:
            ax = x + box_w
            add_text(s, ax, by + box_h / 2 - 0.3, arrow_w, 0.6,
                     "→", size_pt=22, weight=400, color="line_2",
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                     allow_inline=False)
    add_footer(s, meta, page_no, total)


def slide_alert_close(prs, meta, s_data, page_no, total):
    blank = prs.slide_layouts[6]
    s = prs.slides.add_slide(blank)
    add_chapter_tag(s, EDGE_IN, TOP_IN, s_data.get("chapter", ""), small=True)
    add_text(s, EDGE_IN, TOP_IN + 0.4, SLIDE_W_IN - 2 * EDGE_IN, 1.6,
             s_data.get("title", ""), size_pt=40, weight=800,
             color="ink", tracking_em=-0.02, leading=1.08)
    add_text(s, EDGE_IN, TOP_IN + 1.95, SLIDE_W_IN - 2 * EDGE_IN, 0.9,
             s_data.get("lede", ""), size_pt=18, weight=500,
             color="muted_2", leading=1.45, allow_inline=False)
    # Big alert note
    add_text(s, EDGE_IN, TOP_IN + 3.3, SLIDE_W_IN - 2 * EDGE_IN, 2.0,
             s_data.get("alert", ""), size_pt=24, weight=500,
             color="alert_red", leading=1.45)
    add_footer(s, meta, page_no, total)


BUILDERS = {
    "cover":           lambda prs, meta, s, p, t: slide_cover(prs, meta),
    "chapter_divider": slide_chapter_divider,
    "content":         slide_content,
    "card_grid_4":     slide_card_grid_4,
    "stage_flow":      slide_stage_flow,
    "alert_close":     slide_alert_close,
}


def build(data: dict) -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)
    meta = data.get("meta", {})
    slides = data.get("slides", [])
    total = len(slides)
    for i, s in enumerate(slides, 1):
        kind = s.get("type")
        fn = BUILDERS.get(kind)
        if not fn:
            print(f"[warn] unknown slide type: {kind}", file=sys.stderr)
            continue
        fn(prs, meta, s, i, total)
    return prs


def main():
    if len(sys.argv) < 2:
        print("usage: build_pptx.py <input.json> [output.pptx]", file=sys.stderr)
        sys.exit(2)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else OUTPUTS / (in_path.stem + ".pptx")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    prs = build(data)
    prs.save(out_path)
    print(f"OK  PPTX  -> {out_path}")


if __name__ == "__main__":
    main()
