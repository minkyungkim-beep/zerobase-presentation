"""
HTML 슬라이드쇼 → PDF 변환 (Playwright/Chromium).

기존 HTML은 풀스크린 슬라이드쇼 모드라 한 번에 1장만 보임.
PDF로 출력할 때는 모든 슬라이드를 펼치고 각 슬라이드를 1페이지로 떨어뜨려야 함.
"""
from __future__ import annotations
import argparse
import asyncio
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRINT_INJECT_CSS = """
/* ===== Print mode override ===== */
html, body { background: #fff !important; height: auto !important; overflow: visible !important; }
.viewer { position: static !important; display: block !important; }
.stage { box-shadow: none !important; width: 1920px !important; height: auto !important; }
.slide-wrap {
  position: relative !important;
  inset: auto !important;
  opacity: 1 !important; visibility: visible !important;
  width: 1920px !important; height: 1080px !important;
  page-break-after: always;
  break-after: page;
  display: block !important;
}
.slide-wrap:last-child { page-break-after: auto; }
.slide {
  position: absolute !important; top: 0 !important; left: 0 !important;
  transform: none !important;
}
/* hide UI chrome */
.nav-zone, .hud, #help, #edit-toggle, #edit-bar, #toast { display: none !important; }
@page { size: 1920px 1080px; margin: 0; }
"""


async def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.async_api import async_playwright
    file_url = "file://" + str(html_path.resolve())
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await page.goto(file_url, wait_until="networkidle", timeout=60_000)
        # Inject print CSS
        await page.add_style_tag(content=PRINT_INJECT_CSS)
        # Wait briefly for fonts to settle
        await page.evaluate("document.fonts.ready")
        await page.wait_for_timeout(800)
        # Generate PDF
        await page.pdf(
            path=str(pdf_path),
            width="1920px",
            height="1080px",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            prefer_css_page_size=True,
        )
        await browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html", help="path to deck HTML (e.g. outputs/foo.html)")
    ap.add_argument("--out", default=None, help="output PDF path (default: same dir, same stem)")
    args = ap.parse_args()
    html_path = Path(args.html).resolve()
    if not html_path.exists():
        sys.exit(f"파일 없음: {html_path}")
    pdf_path = Path(args.out).resolve() if args.out else html_path.with_suffix(".pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(html_to_pdf(html_path, pdf_path))
    print(f"OK  PDF -> {pdf_path}")


if __name__ == "__main__":
    main()
