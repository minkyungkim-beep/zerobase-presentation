"""
빌드된 자료를 presentations/ 경로 규칙에 맞게 복사 후 GitHub에 자동 커밋·푸시.

경로 규칙:
    presentations/{YYYY-MM}/{Event_Date}_{Type}.pptx
    presentations/{YYYY-MM}/{Event_Date}_{Type}.html
    presentations/{YYYY-MM}/{Event_Date}_{Type}.pdf   (있으면)
    presentations/{YYYY-MM}/{Event_Date}_{Type}.json  (입력 스냅샷)

커밋 메시지:
    [YYYY-MM-DD] 설명회_자료_생성 — {Title}

사용:
    # 1) inputs/2026-05-06_3부.json 빌드 후 푸시
    python3 scripts/git_push.py inputs/2026-05-06_3부.json

    # 2) 빌드를 건너뛰고 기존 outputs만 푸시
    python3 scripts/git_push.py inputs/2026-05-06_3부.json --no-build

    # 3) 푸시는 안 하고 staging만 (커밋 메시지 미리보기)
    python3 scripts/git_push.py inputs/2026-05-06_3부.json --no-push

전제:
    1) 워크스페이스 폴더에서 `python3 scripts/setup_git.sh` 한 번 실행해 git init/remote 완료
    2) macOS Keychain에 GitHub PAT 저장됨 (첫 푸시 때 한번 입력)
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


# ---------- Date / type extraction ----------

DATE_PATTERNS = [
    re.compile(r"(\d{4})[.\-/_](\d{1,2})[.\-/_](\d{1,2})"),  # 2026-05-06 / 2026_05_06
    re.compile(r"(\d{4})(\d{2})(\d{2})"),                     # 20260506
    re.compile(r"(?<!\d)(\d{2})(\d{2})(?!\d)"),               # 0506  (MMDD, 올해)
    re.compile(r"(\d{1,2})[/_\-](\d{1,2})(?!\d)"),            # 5/6 / 5_6 (단독)
]


def _maybe_make_date(groups: tuple[str, ...]) -> datetime | None:
    try:
        if len(groups) == 3:
            y, mo, d = (int(g) for g in groups)
            if y < 100: y += 2000
            return datetime(y, mo, d)
        if len(groups) == 2:
            mo, d = (int(g) for g in groups)
            return datetime(datetime.now().year, mo, d)
    except (ValueError, TypeError):
        return None
    return None


def extract_event_date(meta: dict, fallback_name: str) -> datetime:
    """meta.date 또는 파일명에서 YYYY-MM-DD를 추출. 못 찾으면 오늘 날짜."""
    sources = [meta.get("date", ""), fallback_name]
    for src in sources:
        for pat in DATE_PATTERNS:
            m = pat.search(str(src))
            if not m:
                continue
            d = _maybe_make_date(m.groups())
            if d is not None:
                return d
    print("[warn] 날짜를 추출하지 못해 오늘 날짜로 대체합니다", file=sys.stderr)
    return datetime.now()


def extract_type(meta: dict, fallback_name: str) -> str:
    """설명회 유형 추출 — 1부/2부/3부, 온라인박람회, 직무세미나, 오프라인 등.
    파일명 + meta.session 모두를 살펴 가장 명확한 카테고리를 결정한다."""
    bag = " ".join([str(meta.get("session", "")), str(fallback_name)])
    label = None
    # 우선순위: 오프라인 > 박람회/온라인 > 세미나 > 그룹상담
    for kw, lbl in [
        ("오프라인", "오프라인설명회"),
        ("박람회",   "온라인박람회"),
        ("세미나",   "직무세미나"),
        ("그룹상담", "그룹상담"),
        ("온라인",   "온라인설명회"),
    ]:
        if kw in bag:
            label = lbl
            break
    if label is None:
        label = "온라인설명회"
    m = re.search(r"(\d+)\s*부", bag)
    return f"{label}_{m.group(1)}부" if m else label


# ---------- Build & stage ----------

def build_outputs(input_json: Path) -> dict:
    """build.py를 호출해 outputs/ 에 HTML/PPTX/PDF 생성."""
    print("\n[1/3] 빌드 실행")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "build.py"), str(input_json)],
        cwd=ROOT, text=True, capture_output=True
    )
    print(proc.stdout)
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"build.py 실패 (exit {proc.returncode})")
    stem = input_json.stem
    return {
        "stem": stem,
        "html": ROOT / "outputs" / f"{stem}.html",
        "pptx": ROOT / "outputs" / f"{stem}.pptx",
        "pdf":  ROOT / "outputs" / f"{stem}.pdf",
        "json": input_json,
    }


def stage_to_presentations(built: dict, event_date: datetime, event_type: str) -> list[Path]:
    ymd  = event_date.strftime("%Y-%m-%d")
    ym   = event_date.strftime("%Y-%m")
    target_dir = ROOT / "presentations" / ym
    target_dir.mkdir(parents=True, exist_ok=True)
    base = f"{ymd}_{event_type}"
    print(f"\n[2/3] presentations/{ym}/{base}.* 로 복사")
    copied = []
    for key in ["pptx", "html", "pdf", "json"]:
        src = built[key]
        if not src.exists():
            continue
        dst = target_dir / f"{base}{src.suffix}"
        shutil.copy2(src, dst)
        rel = dst.relative_to(ROOT)
        print(f"  · {rel}")
        copied.append(dst)
    return copied


# ---------- Git ops ----------

def git_commit_push(staged: list[Path], event_date: datetime, title: str, push: bool) -> None:
    print("\n[3/3] git add / commit / push")
    rels = [str(p.relative_to(ROOT)) for p in staged]
    run(["git", "add", "--", *rels])
    msg = f"[{event_date.strftime('%Y-%m-%d')}] 설명회_자료_생성"
    if title:
        msg += f" — {title}"
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"],
                          cwd=ROOT, capture_output=True)
    if diff.returncode == 0:
        print("(stage된 변경 없음 — commit/push 건너뜀)")
        return
    run(["git", "commit", "-m", msg])
    if push:
        try:
            res = run(["git", "push"], check=False)
            if res.returncode != 0:
                print(res.stdout); print(res.stderr, file=sys.stderr)
                print("\n[!] push 실패. 첫 푸시면 다음을 시도하세요:")
                print("    git push -u origin main")
                print("    (또는 기본 브랜치명이 master면 main → master)")
                sys.exit(res.returncode)
        except subprocess.CalledProcessError as e:
            print(e.stderr, file=sys.stderr); raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="inputs/*.json 경로")
    ap.add_argument("--no-build", action="store_true", help="빌드 건너뛰고 기존 outputs 사용")
    ap.add_argument("--no-push",  action="store_true", help="commit까지만 (push 안 함)")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"입력 파일 없음: {in_path}")
    data = json.loads(in_path.read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    title = meta.get("title", "")

    if args.no_build:
        stem = in_path.stem
        built = {
            "stem": stem,
            "html": ROOT / "outputs" / f"{stem}.html",
            "pptx": ROOT / "outputs" / f"{stem}.pptx",
            "pdf":  ROOT / "outputs" / f"{stem}.pdf",
            "json": in_path,
        }
    else:
        built = build_outputs(in_path)

    event_date = extract_event_date(meta, in_path.stem)
    event_type = extract_type(meta, in_path.stem)
    print(f"\n→ event_date={event_date.strftime('%Y-%m-%d')}  type={event_type}")

    staged = stage_to_presentations(built, event_date, event_type)
    git_commit_push(staged, event_date, title, push=not args.no_push)
    print("\n완료.")


if __name__ == "__main__":
    main()
