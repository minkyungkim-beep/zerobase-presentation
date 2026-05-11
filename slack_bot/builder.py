"""
빌드 + 배포 통합 함수.

build_and_publish(data, stem) → HTML/PPTX/PDF 생성 → GitHub 푸시 → URL 반환
"""
from __future__ import annotations
import asyncio
import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import build_pptx  # noqa: E402
import render_html  # noqa: E402

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DECKS_DIR = PROJECT_ROOT / "decks"

log = logging.getLogger(__name__)


def build_and_publish(data: dict, stem: str, github_token: str,
                      github_repo: str) -> dict:
    """
    JSON 데이터를 받아서 HTML / PPTX / PDF 모두 생성하고 GitHub에 푸시.

    Returns:
        dict: {
            "html_path": Path, "pptx_path": Path, "pdf_path": Path,
            "html_url": str (GitHub Pages URL),
            "slide_count": int, "build_seconds": float
        }
    """
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    DECKS_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # 1) HTML
    html_text = render_html.render_deck(data, source_name=stem)
    html_path = OUTPUTS_DIR / f"{stem}.html"
    html_path.write_text(html_text, encoding="utf-8")
    log.info(f"HTML written → {html_path}")

    # 2) PPTX
    pptx_path = OUTPUTS_DIR / f"{stem}.pptx"
    prs = build_pptx.build(data)
    prs.save(str(pptx_path))
    log.info(f"PPTX written → {pptx_path}")

    # 3) PDF
    pdf_path = OUTPUTS_DIR / f"{stem}.pdf"
    asyncio.run(_html_to_pdf(html_path, pdf_path))
    log.info(f"PDF written → {pdf_path}")

    # 4) decks/ 카피 (GitHub Pages 노출용)
    deck_html = DECKS_DIR / f"{stem}.html"
    deck_html.write_text(html_text, encoding="utf-8")

    # 5) GitHub 푸시
    if github_token and github_repo:
        _git_push(github_token=github_token, github_repo=github_repo,
                  files=[deck_html, html_path, pptx_path, pdf_path],
                  message=f"[bot] {stem} 빌드 자동 푸시")

    # 6) 메타
    slide_count = len(data.get("slides", []))
    build_seconds = time.time() - t0
    html_url = f"https://{github_repo.split('/')[0]}.github.io/" \
               f"{github_repo.split('/')[1]}/decks/{stem}.html"

    return {
        "html_path": html_path,
        "pptx_path": pptx_path,
        "pdf_path": pdf_path,
        "html_url": html_url,
        "slide_count": slide_count,
        "build_seconds": build_seconds,
    }


async def _html_to_pdf(html_path: Path, pdf_path: Path):
    """Playwright로 HTML → PDF (모든 슬라이드 펼친 print 모드)."""
    from playwright.async_api import async_playwright
    PRINT_CSS = """
    html, body { background: #fff !important; height: auto !important; overflow: visible !important; }
    .viewer { position: static !important; display: block !important; }
    .stage { box-shadow: none !important; width: 1920px !important; height: auto !important; }
    .slide-wrap {
      position: relative !important; inset: auto !important;
      opacity: 1 !important; visibility: visible !important;
      width: 1920px !important; height: 1080px !important;
      page-break-after: always; break-after: page; display: block !important;
    }
    .slide-wrap:last-child { page-break-after: auto; }
    .slide { position: absolute !important; top: 0 !important; left: 0 !important; transform: none !important; }
    .nav-zone, .hud, #help, #edit-toggle, #edit-bar, #toast { display: none !important; }
    @page { size: 1920px 1080px; margin: 0; }
    """
    file_url = "file://" + str(html_path.resolve())
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await page.goto(file_url, wait_until="networkidle", timeout=60_000)
        await page.add_style_tag(content=PRINT_CSS)
        await page.evaluate("document.fonts.ready")
        await page.wait_for_timeout(800)
        await page.pdf(path=str(pdf_path), width="1920px", height="1080px",
                       print_background=True,
                       margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                       prefer_css_page_size=True)
        await browser.close()


def _git_push(github_token: str, github_repo: str, files: list, message: str):
    """변경사항을 GitHub에 푸시 (간단한 직접 git CLI 호출)."""
    import subprocess
    repo_root = PROJECT_ROOT
    for f in files:
        subprocess.run(["git", "-C", str(repo_root), "add", str(f)], check=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-m", message],
                   check=False)  # 변경 없으면 commit 실패해도 무시
    # push (HTTPS 토큰 인증)
    auth_url = f"https://x-access-token:{github_token}@github.com/{github_repo}.git"
    subprocess.run(["git", "-C", str(repo_root), "push", auth_url, "HEAD:main"],
                   check=True)
    log.info("git push success")
