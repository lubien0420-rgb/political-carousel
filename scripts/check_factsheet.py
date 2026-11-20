"""[팩트 리서처 2/2] factsheet.json 기계 검증.

- 필수 키·형식
- 모든 sources ID가 자료 묶음에 존재
- status=확인 인 사실은 서로 다른 언론사 2곳 이상
- 인용문이 출처 본문에 글자 그대로 존재 (공백·따옴표 차이는 무시)

사용: python scripts/check_factsheet.py data/research/<폴더>
"""
import json
import re
import sys
from pathlib import Path

LISTS = ["facts", "timeline", "numbers", "quotes", "positions", "disputes", "background", "next"]


def norm(s: str) -> str:
    s = re.sub(r"[“”\"'‘’`]", "", s)
    s = s.replace("…", "...").replace("⋯", "...")
    return re.sub(r"\s+", "", s)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    folder = Path(sys.argv[1])
    pack = json.loads((folder / "pack.json").read_text(encoding="utf-8"))
    fs = json.loads((folder / "factsheet.json").read_text(encoding="utf-8"))
    src = {s["id"]: s for s in pack["sources"]}
    errors, warns = [], []

    for k in ["issue", "one_line", *LISTS, "cautions"]:
        if k not in fs:
            errors.append(f"필수 키 없음: {k}")

    def check_ids(where, ids):
        if not ids:
            errors.append(f"{where}: 출처 없음")
        for i in ids or []:
            if i not in src:
                errors.append(f"{where}: 없는 출처 {i}")

    for k in LISTS:
        for n, item in enumerate(fs.get(k, []), 1):
            where = f"{k}[{n}]"
            if k == "disputes":
                for m, v in enumerate(item.get("versions", []), 1):
                    check_ids(f"{where}.versions[{m}]", v.get("sources"))
                continue
            check_ids(where, item.get("sources"))

    for n, f in enumerate(fs.get("facts", []), 1):
        st = f.get("status")
        outlets = {src[i]["source"] for i in f.get("sources", []) if i in src}
        if st not in ("확인", "단독", "불일치"):
            errors.append(f"facts[{n}]: status 값 오류 ({st})")
        elif st == "확인" and len(outlets) < 2:
            errors.append(f"facts[{n}]: '확인'인데 언론사 {len(outlets)}곳 → 2곳 이상 필요 또는 '단독'으로")

    for n, q in enumerate(fs.get("quotes", []), 1):
        text = norm(q.get("quote", ""))
        parts = [p for p in re.split(r"\.\.\.", text) if p]  # 생략부호로 자른 인용은 조각별 확인
        ok = any(all(p in norm(src[i]["body"]) for p in parts)
                 for i in q.get("sources", []) if i in src)
        if not ok:
            errors.append(f"quotes[{n}] 원문 불일치: {q.get('speaker')} “{q.get('quote', '')[:40]}”")

    if len(fs.get("one_line", "")) > 60:
        warns.append(f"one_line {len(fs['one_line'])}자 (60자 이내 권장)")
    sides = {p.get("side", "").split(":")[0] for p in fs.get("positions", [])}
    if len(sides) < 2:
        warns.append("positions 한쪽 입장만 있음")
    used = {i for k in LISTS for it in fs.get(k, []) for i in it.get("sources", [])}
    weak = [s["id"] for s in pack["sources"] if s["body_quality"] != "full" and s["id"] in used]
    if weak:
        warns.append(f"본문 없이 요약만 있는 출처 사용: {', '.join(weak)}")

    c = {k: len(fs.get(k, [])) for k in LISTS}
    print(f"[팩트시트] {fs.get('issue')}")
    print("  " + " · ".join(f"{k} {v}" for k, v in c.items()))
    st = [f.get("status") for f in fs.get("facts", [])]
    print(f"  사실 상태: 확인 {st.count('확인')} / 단독 {st.count('단독')} / 불일치 {st.count('불일치')}")
    for w in warns:
        print(f"  [경고] {w}")
    for e in errors:
        print(f"  [오류] {e}")
    print("  → 통과" if not errors else f"  → 실패 ({len(errors)}건)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
