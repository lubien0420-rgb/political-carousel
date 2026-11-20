"""기사 URL → 본문 텍스트 추출 (언론사 공통 휴리스틱)."""
import re

import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

# 본문 컨테이너로 자주 쓰이는 선택자 (언론사별)
SELECTORS = [
    "[itemprop=articleBody]",
    "#articleBody", "#article_body", "#articletxt", "#article-view-content-div",
    "#news_body_id", "#textBody", "#newsEndContents", "#article_content",
    ".article-body", ".article_body", ".article_txt", ".news_body", ".news_txt",
    ".story-news", ".article-text", ".text_area", ".view_txt", ".art_txt",
    ".viewContent", ".news_text", "article",
]
NOISE = ["script", "style", "noscript", "iframe", "figure", "figcaption", "aside", "nav",
         "footer", "header", "form", "button", "table"]
KO = re.compile(r"[가-힣]")
BOILER = re.compile(r"(무단\s*전재|재배포\s*금지|Copyright|저작권자|기사제보|구독\s*신청|ⓒ|©)")


def _score(el) -> int:
    return len(KO.findall(el.get_text(" ", strip=True)))


def _clean_lines(text: str) -> str:
    out = []
    for line in (l.strip() for l in text.splitlines()):
        if not line or len(line) < 2:
            continue
        if BOILER.search(line) and len(line) < 120:
            continue
        out.append(line)
    return "\n".join(out)


def _jtbc(html: str) -> str:
    """JTBC는 본문이 Next.js 데이터(이스케이프된 JSON 문자열)에만 들어 있다."""
    m = re.search(r'articleInnerTextContent\\":\\"(.*?)\\",\\"', html, re.S)
    if not m:
        return ""
    s = m.group(1)
    for _ in range(2):  # 두 겹 이스케이프 해제
        s = s.encode("latin-1", "backslashreplace").decode("unicode_escape")
    try:
        s = s.encode("latin-1").decode("utf-8")
    except UnicodeError:
        pass
    return _clean_lines(s.replace('\\"', '"'))


def extract(html: str) -> dict:
    jtbc = _jtbc(html) if "articleInnerTextContent" in html else ""
    soup = BeautifulSoup(html, "lxml")
    meta = lambda p: (soup.find("meta", property=p) or soup.find("meta", attrs={"name": p}) or {}).get("content", "")
    title = meta("og:title") or (soup.title.string if soup.title else "")
    desc = meta("og:description") or meta("description")
    published = meta("article:published_time") or meta("og:article:published_time")
    for tag in soup(NOISE):
        tag.decompose()

    best, best_score = None, 0
    for sel in SELECTORS:
        for el in soup.select(sel):
            s = _score(el)
            if s > best_score:
                best, best_score = el, s
        if best_score > 300:  # 앞쪽(구체적) 선택자에서 충분히 찾으면 멈춤
            break
    if best_score < 150:  # 선택자 실패 → 한글이 가장 많이 몰린 div
        for el in soup.find_all(["div", "section"]):
            s = _score(el)
            # 페이지 전체를 감싼 큰 div 대신 <p>가 직접 많은 블록 선호
            if s > best_score and len(el.find_all("div", recursive=False)) < 15:
                best, best_score = el, s
    body = ""
    if best is not None:
        for br in best.find_all("br"):
            br.replace_with("\n")
        body = _clean_lines(best.get_text("\n"))
    if len(jtbc) > len(body):
        body = jtbc
    return {"title": (title or "").strip(), "description": desc.strip(),
            "published": published, "body": body}


def fetch_article(url: str, timeout: int = 20) -> dict:
    r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko"}, timeout=timeout)
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding
    res = extract(r.text)
    res["final_url"] = r.url
    return res
