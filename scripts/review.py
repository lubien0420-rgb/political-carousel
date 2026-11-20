"""[검수] 기계 검증 묶음 + 위험 표현 점검 + 검수자용 문장 목록 / review.json 검증.

사용:
  python scripts/review.py data/research/<폴더>             # 검수 준비 → review_input.md
  python scripts/review.py data/research/<폴더> --validate  # review.json 확인 + 최종 판정
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 비하·모욕 표현 (따옴표 인용 밖에서 쓰이면 경고)
INSULT = ["좌빨", "빨갱이", "수꼴", "토착왜구", "개딸", "대깨", "쓰레기", "미친", "정신병", "매국노",
          "간첩", "범죄자", "사기꾼", "도둑", "개돼지", "벌레", "충(蟲)", "틀딱", "양아치"]
# 범죄 단정 (판결 근거 없이 쓰면 명예훼손 위험)
CRIME = ["횡령했", "뇌물을 받", "조작했", "착복", "비리를 저질", "불법을 저질", "범죄를 저질"]
QUOTED = re.compile(r"[“\"][^”\"]*[”\"]")
SENT = re.compile(r"(?<=[.!?다])\s+")


def run(script: str, folder: Path) -> tuple[str, str]:
    p = subprocess.run([sys.executable, str(HERE / script), str(folder)], capture_output=True,
                       text=True, encoding="utf-8")
    return ("통과" if p.returncode == 0 else "실패"), p.stdout.strip()


def units(cp: dict) -> list[tuple[str, str, str]]:
    """검수 대상 문장 단위 (ID, 위치, 문장)."""
    out = []
    n = 0
    for p in cp["body"]["paragraphs"]:
        for s in (x.strip() for x in SENT.split(p) if x.strip()):
            n += 1
            out.append((f"B{n}", "body", s))
    for i, t in enumerate(cp["titles"], 1):
        out.append((f"T{i}", f"titles[{i-1}]", t["text"]))
    for i, o in enumerate(cp["cover"]["options"], 1):
        out.append((f"C{i}", f"cover.options[{i-1}]", f"{o['line1']} / {o['line2']}"))
    sc = cp["summary_card"]
    out.append(("S0", "summary_card.title", sc["title"]))
    for i, b in enumerate(sc["blocks"], 1):
        out.append((f"S{i}", f"summary_card.blocks[{i-1}]", f"{b['num']} — {b['text']}"))
    out.append(("S4", "summary_card.counter", sc["counter"]["text"]))
    out.append(("S5", "summary_card.claim", sc["claim"]))
    return out


def lint(us) -> list[str]:
    warns = []
    for uid, _, s in us:
        bare = QUOTED.sub("", s)
        for w in INSULT:
            if w in bare:
                warns.append(f"{uid}: 비하·모욕 표현 '{w}' — {s[:40]}")
        for w in CRIME:
            if w in bare:
                warns.append(f"{uid}: 범죄 단정 '{w}' — 판결 근거 확인 필요")
    return warns


def prepare(folder: Path):
    fs_st, fs_out = run("check_factsheet.py", folder)
    cp_st, cp_out = run("check_copy.py", folder)
    cp = json.loads((folder / "copy.json").read_text(encoding="utf-8"))
    us = units(cp)
    lw = lint(us)
    md = ["# 검수 입력", "", "## 기계 검증", "```", fs_out, "", cp_out, "```", "",
          f"## 위험 표현 점검 ({len(lw)}건)", *(f"- {w}" for w in lw or ["없음"]), "",
          "## 검수 대상 문장 (sentence_map에 전부 매핑)", "| ID | 위치 | 문장 |", "|---|---|---|"]
    md += [f"| {u} | {w} | {s} |" for u, w, s in us]
    md += ["", "## 팩트시트 주의사항", *(f"- {c}" for c in json.loads(
        (folder / "factsheet.json").read_text(encoding="utf-8"))["cautions"])]
    (folder / "review_input.md").write_text("\n".join(md), encoding="utf-8")
    print(f"[검수 준비] 팩트시트 {fs_st} · 카피 {cp_st} · 위험 표현 {len(lw)}건 · 문장 {len(us)}개")
    for w in lw:
        print(f"  ! {w}")
    print(f"→ {folder / 'review_input.md'} 를 보고 prompts/reviewer.md 대로 review.json 작성")
    return fs_st == cp_st == "통과"


def validate(folder: Path):
    rv = json.loads((folder / "review.json").read_text(encoding="utf-8"))
    cp = json.loads((folder / "copy.json").read_text(encoding="utf-8"))
    E = []
    ids = {u for u, _, _ in units(cp)}
    mapped = {m["id"] for m in rv.get("sentence_map", [])}
    if ids - mapped:
        E.append(f"sentence_map 누락: {', '.join(sorted(ids - mapped))}")
    for m in rv.get("sentence_map", []):
        if m.get("kind") == "사실" and not m.get("refs"):
            E.append(f"{m['id']}: 사실 문장인데 refs 없음")
    sev = [f.get("severity") for f in rv.get("findings", [])]
    for f in rv.get("findings", []):
        if f.get("severity") not in ("치명", "중요", "경미") or not f.get("fix"):
            E.append(f"finding 형식 오류: {f.get('where')}")
    expect = "게시 불가" if "치명" in sev else "수정 필요" if "중요" in sev else "통과"
    if rv.get("verdict") != expect:
        E.append(f"판정 불일치: review.json '{rv.get('verdict')}' ↔ 심각도 기준 '{expect}'")
    fs_st, _ = run("check_factsheet.py", folder)
    cp_st, _ = run("check_copy.py", folder)
    if "실패" in (fs_st, cp_st) and expect == "통과":
        E.append("기계 검증 실패 상태에서는 통과 불가")

    print(f"[검수 {rv.get('round')}차] {rv.get('issue')}")
    print(f"  기계 검증: 팩트시트 {fs_st} · 카피 {cp_st}")
    print(f"  지적: 치명 {sev.count('치명')} · 중요 {sev.count('중요')} · 경미 {sev.count('경미')}")
    for f in rv.get("findings", []):
        print(f"   - [{f['severity']}] {f['where']}: {f['problem']}")
    for e in E:
        print(f"  [오류] {e}")
    print(f"  판정: {rv.get('verdict')}" + ("" if not E else " (review.json 오류로 무효)"))
    sys.exit(0 if not E and rv.get("verdict") == "통과" else 1)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    folder = Path(sys.argv[1])
    if "--validate" in sys.argv:
        validate(folder)
    else:
        sys.exit(0 if prepare(folder) else 1)


if __name__ == "__main__":
    main()
