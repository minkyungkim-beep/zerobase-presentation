"""
HTML 슬라이드쇼 → Figma 임포트용 "all visible" HTML 변환.

기존 HTML은 풀스크린 슬라이드쇼 모드(JS로 한 장씩만 보여줌)라
html.to.design 같은 Figma 플러그인이 첫 슬라이드만 캡처하게 됨.

이 스크립트는 모든 슬라이드를 세로로 펼쳐서 한 번에 보이게 만든
정적 HTML을 만들어 Figma 플러그인이 통째로 변환할 수 있게 한다.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

FIGMA_INJECT_CSS = """
/* ===== Figma export mode (all slides visible vertically) ===== */
html, body { background: #fff !important; height: auto !important; overflow: visible !important; }
.viewer { position: static !important; display: block !important; padding: 0 !important; }
.stage {
  box-shadow: none !important;
  width: 1920px !important; height: auto !important;
  transform: none !important;
  margin: 0 !important;
}
.slide-wrap {
  position: relative !important;
  inset: auto !important;
  opacity: 1 !important; visibility: visible !important;
  width: 1920px !important; height: 1080px !important;
  display: block !important;
  margin: 0 0 40px 0 !important;
}
.slide {
  position: absolute !important; top: 0 !important; left: 0 !important;
  transform: none !important;
}
/* hide UI chrome */
.nav-zone, .hud, #help, #edit-toggle, #edit-bar, #toast { display: none !important; }
"""


def html_to_figma(html_path: Path, out_path: Path) -> None:
    text = html_path.read_text(encoding="utf-8")
    inject = f"<style id=\"figma-export\">{FIGMA_INJECT_CSS}</style>"
    if "</head>" in text:
        text = text.replace("</head>", inject + "\n</head>", 1)
    else:
        text = inject + "\n" + text
    out_path.write_text(text, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html", help="path to deck HTML (e.g. outputs/foo.html)")
    ap.add_argument("--out", default=None,
                    help="output HTML path (default: same dir, suffix '_figma')")
    args = ap.parse_args()
    html_path = Path(args.html).resolve()
    if not html_path.exists():
        sys.exit(f"파일 없음: {html_path}")
    if args.out:
        out_path = Path(args.out).resolve()
    else:
        out_path = html_path.with_name(html_path.stem + "_figma.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_to_figma(html_path, out_path)
    print(f"OK  Figma HTML -> {out_path}")


if __name__ == "__main__":
    main()
