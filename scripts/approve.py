"""[승인] 사람이 최종 확인하고 제목·표지 안을 고르는 단계. 승인 기록은 approval.json.

- 검수 판정이 '통과'가 아니면 승인할 수 없다.
- 승인은 copy.json·factsheet.json·review.json의 해시에 묶인다. 승인 뒤 파일이 바뀌면 승인은 무효
  (디자이너·업로드 단계가 `approve.py <폴더> --check`로 확인).
- 승인은 반드시 사용자(사람)의 선택으로만 기록한다. Claude가 임의로 고르지 않는다.

사용:
  python scripts/approve.py <폴더>                                  # 승인 패키지 미리보기
  python scripts/approve.py <폴더> --title 2 --cover 3 --ack-notes   # 승인 기록
  python scripts/approve.py <폴더> --reject "사유"                   # 반려 기록
  python scripts/approve.py <폴더> --check                          # 승인 유효성(다음 단계용)
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
BOUND = ["copy.json", "factsheet.json", "review.json"]
IG_CAPTION_MAX = 2200
IG_HASHTAG_MAX = 30


def digest(folder: Path) -> dict:
    return {n: hashlib.sha256((folder / n).read_bytes()).hexdigest()[:16] for n in BOUND}


def review_passed(folder: Path) -> bool:
    p = subprocess.run([sys.executable, str(HERE / "review.py"), str(folder), "--validate"],
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode == 0


def caption(cp: dict, title: str) -> str:
    b = cp["body"]
    return "\n\n".join([title, *b["paragraphs"], b["source_note"].strip("*"), " ".join(cp["hashtags"])])


def load(folder: Path, name: str) -> dict:
    return json.loads((folder / name).read_text(encoding="utf-8"))


def preview(folder: Path):
    cp, rv = load(folder, "copy.json"), load(folder, "review.json")
    ok = review_passed(folder)
    print(f"=== 승인 패키지: {cp['issue']}")
    print(f"검수: {rv['round']}차 '{rv['verdict']}' (검증 {'유효' if ok else '무효 — 승인 불가'})\n")
    print("[제목 후보]")
    for i, t in enumerate(cp["titles"], 1):
        print(f"  {i}. {t['text']}  ({t['type']})")
    print(f"\n[표지 후보]  라벨: {cp['cover']['label']}")
    for i, o in enumerate(cp["cover"]["options"], 1):
        print(f"  {i}. {o['line1']} / {o['line2']}   강조: {o['em']}  ({o['type']})")
    sc = cp["summary_card"]
    print(f"\n[내용정리 카드] {sc['title']}")
    for bl in sc["blocks"]:
        print(f"  {bl['icon']} {bl['label']} · {bl['num']} — {bl['text']}")
    print(f"  {sc['counter']['label']}: {sc['counter']['text']}")
    print(f"  주장: {sc['claim']}")
    cap = caption(cp, cp["titles"][0]["text"])
    print(f"\n[인스타 캡션] (제목 1 기준 {len(cap)}자 / 한도 {IG_CAPTION_MAX}, 해시태그 {len(cp['hashtags'])}/{IG_HASHTAG_MAX})")
    print("  " + cap.replace("\n", "\n  "))
    notes = [f for f in rv["findings"] if f["severity"] == "경미"]
    if notes:
        print("\n[확인 필요한 경미 사항] — 승인 시 --ack-notes 필요")
        for f in notes:
            print(f"  - {f['where']}: {f['problem']}  → {f['fix']}")


def record(folder: Path, a):
    if not review_passed(folder):
        sys.exit("[거부] 검수 판정이 '통과'가 아니거나 검수 기록이 무효입니다.")
    cp, rv = load(folder, "copy.json"), load(folder, "review.json")
    now = datetime.now(KST).isoformat(timespec="seconds")
    if a.reject:
        out = {"status": "반려", "reason": a.reject, "decided_at": now, "decided_by": a.by, "bound": digest(folder)}
    else:
        if not (1 <= a.title <= len(cp["titles"]) and 1 <= a.cover <= len(cp["cover"]["options"])):
            sys.exit("[거부] --title / --cover 번호가 범위를 벗어났습니다.")
        if any(f["severity"] == "경미" for f in rv["findings"]) and not a.ack_notes:
            sys.exit("[거부] 경미 사항을 확인했다는 --ack-notes 가 필요합니다.")
        title = cp["titles"][a.title - 1]["text"]
        cover = dict(cp["cover"]["options"][a.cover - 1])
        cover["label"] = a.label or cp["cover"]["label"]
        cap = caption(cp, title)
        if len(cap) > IG_CAPTION_MAX or len(cp["hashtags"]) > IG_HASHTAG_MAX:
            sys.exit("[거부] 인스타 캡션 한도 초과")
        out = {"status": "승인", "decided_at": now, "decided_by": a.by,
               "title": title, "cover": cover, "caption": cap,
               "acknowledged_notes": [f["problem"] for f in rv["findings"] if f["severity"] == "경미"],
               "review_round": rv["round"], "bound": digest(folder)}
    (folder / "approval.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{out['status']}] {cp['issue']} — {now} by {a.by}")
    if out["status"] == "승인":
        print(f"  제목: {out['title']}\n  표지: {cover['line1']} / {cover['line2']} (강조 {cover['em']}) · 라벨 {cover['label']}")


def check(folder: Path):
    p = folder / "approval.json"
    if not p.exists():
        sys.exit("[무효] 승인 기록 없음")
    ap = json.loads(p.read_text(encoding="utf-8"))
    if ap["status"] != "승인":
        sys.exit(f"[무효] 상태: {ap['status']} ({ap.get('reason')})")
    changed = [n for n, h in digest(folder).items() if ap["bound"].get(n) != h]
    if changed:
        sys.exit(f"[무효] 승인 후 변경된 파일: {', '.join(changed)} → 검수·승인 다시 필요")
    print(f"[유효] {ap['decided_at']} 승인 · 제목 '{ap['title']}'")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--title", type=int)
    ap.add_argument("--cover", type=int)
    ap.add_argument("--label", help="표지 상단 라벨 덮어쓰기")
    ap.add_argument("--ack-notes", action="store_true")
    ap.add_argument("--reject")
    ap.add_argument("--by", default="owner")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    folder = Path(a.folder)
    if a.check:
        check(folder)
    elif a.reject or a.title or a.cover:
        if not a.reject and not (a.title and a.cover):
            sys.exit("--title 과 --cover 를 함께 지정하세요.")
        record(folder, a)
    else:
        preview(folder)


if __name__ == "__main__":
    main()
