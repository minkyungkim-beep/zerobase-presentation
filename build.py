"""
ZeroBase 설명회 자료 자동 생성 - 단일 진입점.

Case 1 (디자인 자동화 모드):
    python build.py inputs/sample_slides.json
        → outputs/sample_slides.html  (미리보기)
        → outputs/sample_slides.pptx  (편집 가능 PPTX)
        → outputs/sample_slides.pdf   (LibreOffice 있으면 자동, 없으면 스킵)

옵션:
    --no-html / --no-pptx / --no-pdf
    --out DIR     출력 폴더 지정
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

import render_html
import build_pptx


def export_pdf_via_libreoffice(pptx_path: Path, out_dir: Path) -> Path | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    cmd = [soffice, "--headless", "--convert-to", "pdf",
           "--outdir", str(out_dir), str(pptx_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        print("[pdf] libreoffice failed:", proc.stderr.strip(), file=sys.stderr)
        return None
    return out_dir / (pptx_path.stem + ".pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="path to slides JSON")
    ap.add_argument("--out", default=str(ROOT / "outputs"))
    ap.add_argument("--no-html", action="store_true")
    ap.add_argument("--no-pptx", action="store_true")
    ap.add_argument("--no-pdf",  action="store_true")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(in_path.read_text(encoding="utf-8"))
    stem = in_path.stem

    html_path = out_dir / f"{stem}.html"
    pptx_path = out_dir / f"{stem}.pptx"

    if not args.no_html:
        html_path.write_text(render_html.render_deck(data, source_name=stem), encoding="utf-8")
        print(f"OK  HTML  -> {html_path}")

    if not args.no_pptx:
        prs = build_pptx.build(data)
        prs.save(pptx_path)
        print(f"OK  PPTX  -> {pptx_path}")

    if not args.no_pdf and pptx_path.exists():
        pdf = export_pdf_via_libreoffice(pptx_path, out_dir)
        if pdf:
            print(f"OK  PDF   -> {pdf}")
        else:
            print("[pdf] LibreOffice not available — skipped (PDF 변환은 옵션)")


if __name__ == "__main__":
    main()
