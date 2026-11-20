"""[수집] 언론사 정치 RSS → 최근 N시간 기사 → 같은 이슈끼리 묶기 → 이슈 후보 순위.

여러 언론사가 동시에 다룬 이슈일수록 위로 올라간다.
결과: data/collected/YYYYMMDD_HHMM.json (+ latest.json), 콘솔에 상위 후보 출력.

사용:
  python scripts/collect.py              # 최근 12시간, 상위 15개
  python scripts/collect.py --hours 24 --top 20
"""
import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))
DC = "{http://purl.org/dc/elements/1.1/}"
ATOM = "{http://www.w3.org/2005/Atom}"

# 제목 앞뒤 머리표·말머리 제거
PREFIX_RE = re.compile(r"^\s*(\[[^\]]{1,12}\]|【[^】]{1,12}】|<[^>]{1,12}>)\s*")
TAG_RE = re.compile(r"<[^>]+>")
WORD_RE = re.compile(r"[가-힣A-Za-z0-9]+")
# 키워드 집계에서 뺄 흔한 말
STOP = {"단독", "속보", "종합", "포토", "영상", "사설", "칼럼", "인터뷰", "오늘", "정치", "기자",
        "대해", "관련", "위해", "통해", "이번", "에서", "으로", "에게", "한다", "했다", "있다", "없다"}
JOSA = ("에서는", "으로는", "에게는", "이라는", "에서", "으로", "에게", "까지", "부터", "보다", "처럼",
        "이라", "라는", "하는", "했다", "한다", "은", "는", "이", "가", "을", "를", "의", "에", "도", "와", "과", "로", "만")


def parse_date(s: str | None):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=KST)
    return d


def clean(text: str | None) -> str:
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def fetch(feed: dict, ua: str) -> tuple[str, list[dict], str | None]:
    try:
        r = requests.get(feed["url"], headers={"User-Agent": ua}, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:  # 피드 하나 실패해도 전체는 계속
        return feed["name"], [], f"{type(e).__name__}: {str(e)[:120]}"
    out = []
    for it in root.findall(".//item") + root.findall(f".//{ATOM}entry"):
        title = clean(it.findtext("title") or it.findtext(f"{ATOM}title"))
        link = (it.findtext("link") or "").strip()
        if not link:
            el = it.find(f"{ATOM}link")
            link = el.get("href", "") if el is not None else ""
        date = parse_date(it.findtext("pubDate") or it.findtext(f"{DC}date")
                          or it.findtext(f"{ATOM}published") or it.findtext(f"{ATOM}updated"))
        if feed.get("via") == "google":  # "제목 - 언론사" 꼬리 제거
            title = re.sub(r"\s+-\s+[^-]{1,20}$", "", title)
        if not title:
            continue
        out.append({
            "source": feed["name"],
            "title": title,
            "link": link,
            "published": date.astimezone(KST).isoformat() if date else None,
            "summary": "" if feed.get("via") == "google" else clean(it.findtext("description"))[:300],
        })
    return feed["name"], out, None


def norm_title(t: str) -> str:
    while PREFIX_RE.match(t):
        t = PREFIX_RE.sub("", t, count=1)
    return t


def words(t: str) -> list[str]:
    res = []
    for w in WORD_RE.findall(norm_title(t)):
        for j in JOSA:
            if len(w) > len(j) + 1 and w.endswith(j):
                w = w[: -len(j)]
                break
        if len(w) >= 2 and w not in STOP:
            res.append(w)
    return res


def bigrams(t: str) -> set[str]:
    s = re.sub(r"[^가-힣A-Za-z0-9]", "", norm_title(t))
    return {s[i:i + 2] for i in range(len(s) - 1)}


def cluster(arts: list[dict], th: float) -> list[list[int]]:
    """제목 글자 2-gram 유사도(겹침 계수)로 union-find 묶기."""
    grams = [bigrams(a["title"]) for a in arts]
    parent = list(range(len(arts)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(arts)):
        for j in range(i + 1, len(arts)):
            a, b = grams[i], grams[j]
            if not a or not b:
                continue
            sim = len(a & b) / min(len(a), len(b))
            # 공통 2-gram이 충분히 많아야 연결 (짧은 제목끼리 우연히 겹치는 것 방지)
            if sim >= th and len(a & b) >= 6:
                parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i in range(len(arts)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=12)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--threshold", type=float, default=0.45)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    cfg = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
    now = datetime.now(KST)
    since = now - timedelta(hours=a.hours)

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(lambda f: fetch(f, cfg["user_agent"]), cfg["feeds"]))

    arts, seen, feed_stats = [], set(), []
    for name, items, err in results:
        kept = 0
        for x in items:
            d = datetime.fromisoformat(x["published"]) if x["published"] else None
            if d is None or d > now + timedelta(minutes=10):  # 날짜 없음/미래 날짜는 수집 시각으로 대체
                x["published"] = now.isoformat(timespec="seconds")
                x["date_estimated"] = True
                d = now
            if d < since:
                continue
            key = re.sub(r"\W", "", norm_title(x["title"]))
            if key in seen:
                continue
            seen.add(key)
            arts.append(x)
            kept += 1
        feed_stats.append({"source": name, "fetched": len(items), "kept": kept, "error": err})

    issues = []
    for g in cluster(arts, a.threshold):
        members = sorted((arts[i] for i in g), key=lambda x: x["published"], reverse=True)
        outlets = sorted({m["source"] for m in members})
        kw = Counter(w for m in members for w in set(words(m["title"])))
        latest = max(datetime.fromisoformat(m["published"]) for m in members)
        age_h = (now - latest).total_seconds() / 3600
        score = len(outlets) * 10 + len(members) * 2 - age_h  # 다룬 언론사 수 > 기사 수 > 최신성
        issues.append({
            "headline": norm_title(members[0]["title"]),
            "keywords": [w for w, _ in kw.most_common(6)],
            "outlet_count": len(outlets),
            "article_count": len(members),
            "outlets": outlets,
            "latest": latest.isoformat(timespec="minutes"),
            "score": round(score, 1),
            "articles": members,
        })
    issues.sort(key=lambda x: x["score"], reverse=True)
    for i, it in enumerate(issues, 1):
        it["rank"] = i

    out_dir = ROOT / "data" / "collected"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "collected_at": now.isoformat(timespec="seconds"),
        "window_hours": a.hours,
        "feeds": feed_stats,
        "article_total": len(arts),
        "issues": issues,
    }
    path = out_dir / f"{now:%Y%m%d_%H%M}.json"
    for p in (path, out_dir / "latest.json"):
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[수집] {now:%Y-%m-%d %H:%M} KST, 최근 {a.hours:g}시간, 기사 {len(arts)}건 → 이슈 {len(issues)}개")
    bad = [f for f in feed_stats if f["error"] or f["kept"] == 0]
    for f in bad:
        print(f"  ! {f['source']}: {f['error'] or '기간 내 기사 없음'}")
    print()
    for it in issues[: a.top]:
        print(f"{it['rank']:>2}. [{it['outlet_count']}개사/{it['article_count']}건] {it['headline']}")
        print(f"     키워드: {', '.join(it['keywords'])} | {', '.join(it['outlets'])}")
    print(f"\n저장: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
