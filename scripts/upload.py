"""[업로드 + 로그] 승인된 최종 이미지 → JPEG 변환 → GitHub Pages 공개 → 인스타 캐러셀 게시 → 로그.

전제:
  - approve.py --check 유효 (승인 후 카피·팩트시트·검수 파일이 바뀌지 않았어야 함)
  - <폴더>/final/slide1.png, slide2.png (디자이너 HTML에서 사진 넣고 받은 파일; .jpg도 가능)
  - 같은 폴더로 이미 게시했으면(published.json) 거부 → 중복 게시 방지

사용:
  python scripts/upload.py data/research/<폴더> --dry-run   # 변환·점검만 (push·게시 없음)
  python scripts/upload.py data/research/<폴더>             # 실제 게시
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
KST = timezone(timedelta(hours=9))
PAGES_BASE = "https://lubien0420-rgb.github.io/political-carousel"
SIZE = 1080
MAX_BYTES = 8 * 1024 * 1024
SLIDES = 2


def git(*args):
    cmd = ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential", *args]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        sys.exit(f"[git 오류] {' '.join(args)}\n{p.stderr.strip()}")
    return p.stdout.strip()


def find_slide(final: Path, n: int) -> Path:
    for ext in ("png", "jpg", "jpeg"):
        p = final / f"slide{n}.{ext}"
        if p.exists():
            return p
    sys.exit(f"[거부] {final}/slide{n}.png 가 없습니다 (디자이너 HTML에서 받은 파일을 넣어 주세요).")


def to_jpeg(src: Path, dst: Path):
    im = Image.open(src)
    w, h = im.size
    if abs(w - h) > 2:
        sys.exit(f"[거부] {src.name} 이 정사각형이 아닙니다 ({w}x{h}).")
    if w < SIZE:
        sys.exit(f"[거부] {src.name} 해상도 부족 ({w}x{h}, 최소 {SIZE}).")
    im = im.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
    for q in (92, 88, 84, 80):
        im.save(dst, "JPEG", quality=q, optimize=True, progressive=False)
        if dst.stat().st_size <= MAX_BYTES:
            return
    sys.exit(f"[거부] {dst.name} 8MB 초과")


def wait_public(urls: list[str], timeout=300):
    end = time.time() + timeout
    pending = list(urls)
    while pending and time.time() < end:
        pending = [u for u in pending
                   if not (lambda r: r.status_code == 200 and "jpeg" in r.headers.get("Content-Type", ""))(
                       requests.head(u, timeout=20, allow_redirects=True))]
        if pending:
            time.sleep(10)
    if pending:
        sys.exit(f"[오류] Pages 반영 시간 초과: {pending}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    folder = Path(a.folder).resolve()

    # 1) 게이트
    if (folder / "published.json").exists():
        sys.exit(f"[거부] 이미 게시됨: {json.loads((folder / 'published.json').read_text(encoding='utf-8'))['permalink']}")
    chk = subprocess.run([sys.executable, str(ROOT / "scripts" / "approve.py"), str(folder), "--check"],
                         capture_output=True, text=True, encoding="utf-8")
    if chk.returncode != 0:
        sys.exit(f"[거부] 승인 무효: {(chk.stdout + chk.stderr).strip()}")
    approval = json.loads((folder / "approval.json").read_text(encoding="utf-8"))
    print(f"[1] 승인 유효 · {approval['decided_at']} · 제목 '{approval['title']}'")

    # 2) 이미지 변환
    post_id = re.match(r"\d{8}_\d{4}_r\d+", folder.name).group(0)
    rel = f"docs/posts/{post_id}"
    out_dir = Path(tempfile.mkdtemp()) if a.dry_run else ROOT / rel
    out_dir.mkdir(parents=True, exist_ok=True)
    for n in range(1, SLIDES + 1):
        to_jpeg(find_slide(folder / "final", n), out_dir / f"slide{n}.jpg")
        print(f"[2] slide{n}.jpg {SIZE}x{SIZE} {(out_dir / f'slide{n}.jpg').stat().st_size // 1024}KB")
    urls = [f"{PAGES_BASE}/posts/{post_id}/slide{n}.jpg" for n in range(1, SLIDES + 1)]
    print(f"[3] 캡션 {len(approval['caption'])}자 · 공개 URL 예정 {urls[0]} …")
    if a.dry_run:
        print(f"[dry-run] 변환본: {out_dir} — push·게시는 하지 않았습니다.")
        return

    # 3) GitHub Pages 공개
    git("add", rel)
    git("commit", "-m", f"post {post_id}: carousel images",
        "-m", "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    git("push", "-q")
    print("[4] push 완료 · Pages 반영 대기")
    wait_public(urls)

    # 4) 인스타 게시
    from ig_common import ApiError
    from publish_carousel import publish
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    rec = {"post_id": post_id, "folder": folder.name, "issue": approval["title"],
           "approved_at": approval["decided_at"], "image_urls": urls,
           "attempted_at": datetime.now(KST).isoformat(timespec="seconds")}
    try:
        res = publish(urls, approval["caption"])
        rec.update(status="published", **res)
        (folder / "published.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    except (ApiError, ValueError) as e:
        rec.update(status="failed", error=str(e))
        print("[API 오류]\n" + str(e))
    # 5) 로그 (성공·실패 모두)
    with open(log_dir / "posts.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[5] 로그 기록 logs/posts.jsonl · 상태 {rec['status']}"
          + (f" · {rec.get('permalink')}" if rec["status"] == "published" else ""))
    sys.exit(0 if rec["status"] == "published" else 1)


if __name__ == "__main__":
    main()
