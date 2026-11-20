"""[카피] copy.json 기계 검증 — 규격(republican-short) + 팩트시트 대조.

사용: python scripts/check_copy.py data/research/<폴더>
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUOTE_RE = re.compile(r"[“\"]([^”\"]{4,})[”\"]")
NUM_RE = re.compile(r"\d[\d,.]*")
META = ["숏폼", "현황 파트", "의견 파트", "후반부", "전반부"]
EMO = ["분노", "어이없", "기가 막", "황당", "참담", "개탄"]


# 표지 한 줄: 84px ExtraBold, letter-spacing -2px, 좌우 패딩 24px씩, nowrap → 카드 폭 1080 안에 여유 두고
COVER_MAX = 1080 - 48 - 80


def cover_width(text: str) -> int:
    """표지 줄의 대략적 렌더 폭(px). Pretendard 대신 굵은 한글 시스템 폰트로 근사."""
    try:
        from PIL import ImageFont
        for name in ("Pretendard-ExtraBold.otf", "malgunbd.ttf", "NotoSansKR-Bold.otf"):
            try:
                f = ImageFont.truetype(name, 84)
                break
            except OSError:
                f = None
        if f:
            return int(f.getlength(text) - 2 * max(len(text) - 1, 0))
    except ImportError:
        pass
    return sum(84 if re.match(r"[가-힣]", c) else 40 for c in text)


def norm(s: str) -> str:
    s = re.sub(r"[“”\"'‘’`]", "", s).replace("…", "...").replace("⋯", "...")
    return re.sub(r"\s+", "", s)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    folder = Path(sys.argv[1])
    cp = json.loads((folder / "copy.json").read_text(encoding="utf-8"))
    fs = json.loads((folder / "factsheet.json").read_text(encoding="utf-8"))
    pack = json.loads((folder / "pack.json").read_text(encoding="utf-8"))
    E, W = [], []

    # --- 제목
    titles = cp.get("titles", [])
    if len(titles) != 3:
        E.append(f"제목 {len(titles)}개 (3개 필요)")
    for t in titles:
        if not t.get("type"):
            E.append(f"제목 유형 누락: {t.get('text')}")
        if len(t.get("text", "")) > 32:
            W.append(f"제목 {len(t['text'])}자 (25자 안팎 권장): {t['text']}")

    # --- 본문
    b = cp.get("body", {})
    paras = b.get("paragraphs", [])
    body = "\n\n".join(paras)
    n = len(body.replace("\n", ""))
    if not 450 <= n <= 550:
        E.append(f"본문 {n}자 (공백 포함 450~550자)")
    if not 3 <= len(paras) <= 6:
        W.append(f"문단 {len(paras)}개 (현황 1~2 + 전환 1 + 의견 1~2 권장)")
    if b.get("transition") not in paras:
        E.append("transition이 paragraphs 안에 없음")
    if not any(len(p) <= 40 for p in paras):
        E.append("한 줄짜리 문단 없음")
    if not body.rstrip().endswith(b.get("closing", "\0")):
        E.append("closing이 본문 마지막 문장과 다름")
    if body.count("?") > 1:
        E.append(f"반문/질문 {body.count('?')}회 (1회 이내)")
    emo = [w for w in EMO if w in body]
    if len(emo) > 1:
        E.append(f"감정어 {len(emo)}개: {emo} (최대 1개)")
    if not b.get("source_note"):
        E.append("출처 안내 줄 없음")

    # --- 해시태그
    tags = cp.get("hashtags", [])
    if len(tags) != 20 or len(set(tags)) != 20:
        E.append(f"해시태그 {len(tags)}개(중복 제외 {len(set(tags))}) — 정확히 20개")
    for t in tags:
        if not re.fullmatch(r"#[가-힣A-Za-z0-9]+", t):
            E.append(f"해시태그 형식 오류: {t}")
        elif len(t) > 8:
            W.append(f"해시태그가 김(잘게 쪼개기): {t}")

    # --- 표지
    cv = cp.get("cover", {})
    if not cv.get("label") or "·" not in cv.get("label", ""):
        W.append("표지 라벨이 '사건 · 날짜' 형식 아님")
    opts = cv.get("options", [])
    if len(opts) != 3:
        E.append(f"표지 안 {len(opts)}개 (3개 필요)")
    for i, o in enumerate(opts, 1):
        if not o.get("line1") or not o.get("line2"):
            E.append(f"표지 {i}안: 2줄 필요")
        if not o.get("em") or o["em"] not in o.get("line2", ""):
            E.append(f"표지 {i}안: 강조 단어가 2줄 안에 없음")
        for k in ("line1", "line2"):
            w = cover_width(o.get(k, ""))
            if w > COVER_MAX:
                E.append(f"표지 {i}안 {k} 폭 {w}px > {COVER_MAX}px (카드 밖으로 잘림): {o[k]}")
        if any(norm(o.get("line1", "") + o.get("line2", "")) == norm(t.get("text", "")) for t in titles):
            E.append(f"표지 {i}안이 제목과 동일")

    # --- 내용정리 카드
    sc = cp.get("summary_card", {})
    if len(sc.get("blocks", [])) != 3:
        E.append("내용정리 팩트 블록 3개 필요")
    for i, bl in enumerate(sc.get("blocks", []), 1):
        for k in ("icon", "label", "num", "text"):
            if not bl.get(k):
                E.append(f"블록{i} {k} 누락")
        if bl.get("label") and not re.fullmatch(r"[A-Z0-9 &·./-]+", bl["label"]):
            W.append(f"블록{i} 라벨은 영문 대문자 권장: {bl['label']}")
    if not sc.get("counter", {}).get("text"):
        E.append("상대측 입장 블록 없음")
    if not sc.get("claim"):
        E.append("하단 주장 없음")

    # --- 팩트 대조: 인용·숫자
    all_copy = "\n".join([body, *(t.get("text", "") for t in titles),
                          *(o.get("line1", "") + " " + o.get("line2", "") for o in opts),
                          sc.get("title", ""), sc.get("claim", ""), sc.get("counter", {}).get("text", ""),
                          *(bl.get("num", "") + " " + bl.get("text", "") for bl in sc.get("blocks", []))])
    src_text = norm(" ".join(s["body"] + " " + s["title"] for s in pack["sources"]))
    for q in QUOTE_RE.findall(all_copy):
        parts = [p for p in norm(q).split("...") if p]
        if not all(p in src_text for p in parts):
            E.append(f"인용 원문 불일치: “{q[:40]}”")
    fs_text = json.dumps(fs, ensure_ascii=False)
    fs_digits = set(re.findall(r"\d+", fs_text))
    for num in set(NUM_RE.findall(all_copy)):
        for d in re.findall(r"\d+", num.replace(",", "")):
            if d not in fs_digits and d not in fs_text:
                E.append(f"팩트시트에 없는 숫자: {num}")

    # --- 메타 노출
    for m in META:
        if m in body:
            E.append(f"본문에 메타 표현 노출: {m}")

    # --- cautions 대응
    cc = cp.get("caution_check", [])
    if len(cc) < len(fs.get("cautions", [])):
        E.append(f"caution_check {len(cc)}개 < factsheet cautions {len(fs['cautions'])}개")

    # --- 이전 카피와 전환·마무리 반복
    for other in (ROOT / "data" / "research").glob("*/copy.json"):
        if other.parent.resolve() == folder.resolve():
            continue
        o = json.loads(other.read_text(encoding="utf-8")).get("body", {})
        if o.get("transition") == b.get("transition"):
            W.append(f"전환 문구가 이전 글과 같음 ({other.parent.name})")
        if o.get("closing") == b.get("closing"):
            W.append(f"마무리 문장이 이전 글과 같음 ({other.parent.name})")

    print(f"[카피] {cp.get('issue')}")
    print(f"  본문 {n}자 · 문단 {len(paras)} · 해시태그 {len(tags)} · 표지 {len(opts)}안")
    for w in W:
        print(f"  [경고] {w}")
    for e in E:
        print(f"  [오류] {e}")
    print("  → 통과" if not E else f"  → 실패 ({len(E)}건)")
    sys.exit(1 if E else 0)


if __name__ == "__main__":
    main()
