"""[디자이너] 승인된 카피 → 1:1 캐러셀 2장 HTML (templates/carousel_politics_1x1.html).

- 기본: 승인(approval.json)이 유효해야 만든다. 승인된 제목·표지 안을 쓴다.
- --draft: 승인 전 레이아웃 확인용 시안. 상단에 '미승인 시안' 띠가 붙고 파일명도 _DRAFT.
  시안으로는 업로드 단계가 진행되지 않는다.
- 배경 사진은 넣지 않는다(사용자가 HTML에서 직접 업로드).

사용:
  python scripts/design.py data/research/<폴더>
  python scripts/design.py data/research/<폴더> --draft --cover 1
"""
import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "carousel_politics_1x1.html"
BRAND = "TRENDCHATTER"  # 템플릿(republican-short) 기본 브랜드. 바꾸려면 여기만 수정

BLOCK = """    <div class="sector-block">
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
    a = ap.parse_args()
    folder = Path(a.folder).resolve()
    cp =json.loads((folder / "copy.json").read_text(encoding="utf-8"))

    if a.draft:
        cover = dict(cp["cover"]["options"][a.cover - 1], label=cp["cover"]["label"])
        out = folder / "design" / f"carousel_politics_1x1_DRAFT_cover{a.cover}.html"
        banner = '<div class="draft-banner">미승인 시안 — 레이아웃 확인용. 업로드에 쓰지 마세요.</div>'
    else:
        chk = subprocess.run([sys.executable, str(ROOT / "scripts" / "approve.py"), str(folder), "--check"],
                             capture_output=True, text=True, encoding="utf-8")
        if chk.returncode != 0:
            sys.exit(f"[거부] 승인이 유효하지 않습니다: {(chk.stdout + chk.stderr).strip()}")
        cover = json.loads((folder / "approval.json").read_text(encoding="utf-8"))["cover"]
        out = folder / "design" / "carousel_politics_1x1.html"
        banner = ""

    l2 = cover["line2"]
    i = l2.index(cover["em"])
    sc = cp["summary_card"]
    rep = {
        "{{BRAND}}": BRAND,
        "{{DRAFT_BANNER}}": banner,
        "{{COVER_LABEL}}": e(cover["label"]),
        "{{COVER_LINE1}}": e(cover["line1"]),
        "{{COVER_LINE2_BEFORE}}": e(l2[:i]),
        "{{COVER_EM}}": e(cover["em"]),
        "{{COVER_LINE2_AFTER}}": e(l2[i + len(cover["em"]):]),
        "{{S2_TITLE}}": e(sc["title"]),
        "{{BLOCKS}}": "\n".join(BLOCK.format(**{k: e(v) for k, v in b.items()}) for b in sc["blocks"]),
        "{{COUNTER_LABEL}}": e(sc["counter"]["label"]),
        "{{COUNTER_TEXT}}": e(sc["counter"]["text"]),
        "{{CLAIM}}": e(sc["claim"]),
    }
    page = TEMPLATE.read_text(encoding="utf-8")
    for k, v in rep.items():
        page = page.replace(k, v)
    left = [t for t in ("{{",) if t in page]
    if left:
        sys.exit("[오류] 템플릿 자리표시자가 남았습니다.")
    out.parent.mkdir(exist_ok=True)
    (folder / "final").mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"[디자인{' 시안' if a.draft else ''}] {out.relative_to(ROOT)}")
    print("다음(수동): 브라우저로 열기 → 카드 1·2 배경 사진 업로드 → '전체 2장 다운로드' →"
          f" 받은 slide1.png, slide2.png를 {(folder / 'final').relative_to(ROOT)} 에 넣기")


if __name__ == "__main__":
    main()
