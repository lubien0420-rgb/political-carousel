"""[팩트 리서처 1/2] 지정한 이슈의 기사 본문을 모아 '자료 묶음'을 만든다.

판단(팩트시트 작성)은 Claude Code가 prompts/fact_researcher.md 규칙에 따라 수행하고,
scripts/check_factsheet.py 로 출처·인용을 기계 검증한다.

사용:
  python scripts/collect.py                 # 먼저 수집
  python scripts/research_pack.py --rank 1  # 순위 1번 이슈 자료 묶음
  python scripts/research_pack.py --rank 3 --max 12 --collected data/collected/20261121_0900.json
"""
import argparse
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from article_text import fetch_article

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
BODY_MAX = 5000
MIN_BODY = 200


def slug(text: str) -> str:
    s = re.sub(r"[^가-힣A-Za-z0-9]+", "-", text).strip("-")
    return s[:30]


def pick(articles: list[dict], n: int) -> list[dict]:
    """언론사가 고르게 섞이도록 라운드로빈. 같은 언론사 안에서는 '종합' 기사·긴 제목 우선."""
    by: dict[str, list[dict]] = defaultdict(list)
    for a in articles:
        by[a["source"]].append(a)
    for lst in by.values():
        lst.sort(key=lambda a: ("종합" in a["title"], len(a["title"])), reverse=True)
    order = sorted(by, key=lambda s: -len(by[s]))
    out = []
    while len(out) < n and any(by.values()):
        for s in order:
            if by[s] and len(out) < n:
                out.append(by[s].pop(0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rank", type=int, required=True)
    ap.add_argument("--max", type=int, default=10, help="본문을 받을 기사 수")
    ap.add_argument("--collected", default=str(ROOT / "data" / "collected" / "latest.json"))
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    col = json.loads(Path(a.collected).read_text(encoding="utf-8"))
    issue = next((i for i in col["issues"] if i["rank"] == a.rank), None)
    if not issue:
        sys.exit(f"순위 {a.rank} 이슈가 없습니다.")

    # 본문을 받을 수 없는 Google 뉴스 링크는 '보도 목록'에만 남긴다
    fetchable = [x for x in issue["articles"] if "news.google.com" not in x["link"]]
    chosen = pick(fetchable, a.max)

    sources = []
    for i, art in enumerate(chosen, 1):
        sid = f"S{i}"
        rec = {"id": sid, "source": art["source"], "title": art["title"], "url": art["link"],
               "published": art["published"], "body": "", "body_quality": "full"}
        try:
            got = fetch_article(art["link"])
            body = got["body"]
            if len(body) < MIN_BODY:
                body = "\n".join(x for x in (got["description"], art.get("summary", "")) if x)
                rec["body_quality"] = "summary_only"
            rec["body"] = body[:BODY_MAX]
        except Exception as e:
            rec["body"] = art.get("summary", "")
            rec["body_quality"] = f"fetch_failed: {type(e).__name__}"
        sources.append(rec)
        print(f"  {sid} {art['source']:5} {rec['body_quality']:13} {len(rec['body']):5}자  {art['title'][:45]}")
        time.sleep(0.5)  # 언론사 서버 배려

    now = datetime.now(KST)
    out_dir = ROOT / "data" / "research" / f"{now:%Y%m%d_%H%M}_r{a.rank}_{slug(issue['headline'])}"
    out_dir.mkdir(parents=True, exist_ok=True)
    pack = {
        "issue": issue["headline"],
        "rank": a.rank,
        "keywords": issue["keywords"],
        "collected_at": col["collected_at"],
        "packed_at": now.isoformat(timespec="seconds"),
        "coverage": {"outlets": issue["outlets"], "article_count": issue["article_count"],
                     "all_titles": [f"{x['source']} | {x['title']}" for x in issue["articles"]]},
        "sources": sources,
    }
    (out_dir / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# 자료 묶음: {issue['headline']}",
          f"- 수집 {col['collected_at']} / 묶음 {pack['packed_at']}",
          f"- 보도: {len(issue['outlets'])}개사 {issue['article_count']}건 ({', '.join(issue['outlets'])})",
          "", "## 전체 보도 제목 (본문 미수집 포함)"]
    md += [f"- {t}" for t in pack["coverage"]["all_titles"]]
    for s in sources:
        md += ["", f"## [{s['id']}] {s['source']} · {s['title']}",
               f"{s['published']} · {s['url']} · 본문상태={s['body_quality']}", "", s["body"]]
    (out_dir / "pack.md").write_text("\n".join(md), encoding="utf-8")

    full = sum(1 for s in sources if s["body_quality"] == "full")
    print(f"\n[자료 묶음] 본문 {full}/{len(sources)}건 확보 → {out_dir.relative_to(ROOT)}")
    print("다음: prompts/fact_researcher.md 규칙으로 factsheet.json 작성 → python scripts/check_factsheet.py "
          f"{out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
