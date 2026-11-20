"""[디자이너] 승인된 카피 → 1:1 캐러셀 2장 HTML.

스타일 (--style):
  tabloid (기본) templates/carousel_tabloid_1x1.html  — 사진 꽉 채운 표지 + 굵은 외곽선 헤드라인 + 신문지 정리 카드
  classic        templates/carousel_politics_1x1.html — republican-short 원본(검정·골드)

- 기본: 승인(approval.json)이 유효해야 만든다. 승인된 표지 안을 쓴다.
- --draft: 승인 전 레이아웃 시안. '미승인 시안' 띠 + 파일명 _DRAFT. 업로드에 쓰지 않는다.
- 배경 사진은 넣지 않는다(사용자가 HTML에서 직접 업로드).

사용:
  python scripts/design.py data/research/<폴더>
  python scripts/design.py data/research/<폴더> --draft --cover 2 [--style classic]
"""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = {"tabloid": "carousel_tabloid_1x1.html", "classic": "carousel_politics_1x1.html"}
HANDLE = "@politicsinsight360"
CLASSIC_BRAND = "TRENDCHATTER"
CLASSIC_BLOCK = """    <div class="sector-block">
      <div class="sector-icon">{icon}</div>
      <div class="sector-content">
        <div class="sector-label">{label}</div>
        <div class="sector-num">{num}</div>
        <div class="sector-text">{text}</div>
      </div>
    </div>"""


def e(s: str) -> str:
    return html.escape(s, quote=False)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--cover", type=int, default=1, help="--draft일 때 볼 표지 안 번호")
    ap.add_argument("--style", choices=TEMPLATES, default="tabloid")
    a = ap.parse_args()
    folder = Path(a.folder).resolve()
    cp = json.loads((folder / "copy.json").read_text(encoding="utf-8"))

    if a.draft:
        cover = dict(cp["cover"]["options"][a.cover - 1], label=cp["cover"]["label"])
        out = folder / "design" / f"{a.style}_DRAFT_cover{a.cover}.html"
        banner = '<div class="draft-banner">미승인 시안 — 레이아웃 확인용. 업로드에 쓰지 마세요.</div>'
    else:
        chk = subprocess.run([sys.executable, str(ROOT / "scripts" / "approve.py"), str(folder), "--check"],
                             capture_output=True, text=True, encoding="utf-8")
        if chk.returncode != 0:
            sys.exit(f"[거부] 승인이 유효하지 않습니다: {(chk.stdout + chk.stderr).strip()}")
        cover = json.loads((folder / "approval.json").read_text(encoding="utf-8"))["cover"]
        out = folder / "design" / f"{a.style}.html"
        banner = ""

    page = (ROOT / "templates" / TEMPLATES[a.style]).read_text(encoding="utf-8")
    m = re.search(r"<!--BLOCK_START\n(.*?)\nBLOCK_END-->", page, re.S)
    block_tpl = m.group(1) if m else CLASSIC_BLOCK
    sc = cp["summary_card"]
    blocks = "\n".join(block_tpl.format(idx=f"{i:02d}", **{k: e(v) for k, v in b.items()})
                       for i, b in enumerate(sc["blocks"], 1))
    l2, em = cover["line2"], cover["em"]
    i = l2.index(em)
    tag, _, date = cover["label"].partition(" · ")
    rep = {
        "{{BRAND}}": CLASSIC_BRAND, "{{HANDLE}}": HANDLE, "{{DRAFT_BANNER}}": banner,
        "{{COVER_LABEL}}": e(cover["label"]), "{{TAG}}": e(tag), "{{DATE}}": e(date or ""),
        "{{COVER_LINE1}}": e(cover["line1"]), "{{COVER_LINE2_BEFORE}}": e(l2[:i]),
        "{{COVER_EM}}": e(em), "{{COVER_LINE2_AFTER}}": e(l2[i + len(em):]),
        "{{S2_TITLE}}": e(sc["title"]), "{{BLOCKS}}": blocks,
        "{{COUNTER_LABEL}}": e(sc["counter"]["label"]), "{{COUNTER_TEXT}}": e(sc["counter"]["text"]),
        "{{CLAIM}}": e(sc["claim"]),
    }
    for k, v in rep.items():
        page = page.replace(k, v)
    if re.search(r"\{\{[A-Z0-9_]+\}\}", page):
        sys.exit("[오류] 템플릿 자리표시자가 남았습니다: " + ", ".join(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", page))))
    out.parent.mkdir(exist_ok=True)
    (folder / "final").mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"[디자인{' 시안' if a.draft else ''} · {a.style}] {out.relative_to(ROOT)}")
    print("다음(수동): 브라우저로 열기 → 표지·카드2 사진 업로드 → '전체 2장 다운로드' →"
          f" slide1.png, slide2.png를 {(folder / 'final').relative_to(ROOT)} 에 넣기")


if __name__ == "__main__":
    main()
