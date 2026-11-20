"""캐러셀 게시: 이미지별 컨테이너 → 캐러셀 컨테이너 → media_publish → permalink 확인.

사용:
  python scripts/publish_carousel.py --caption "..." URL1 URL2 [...]
  python scripts/publish_carousel.py --dry-run URL1 URL2   # URL 접근성만 점검
"""
import argparse
import sys
import time

import requests

from ig_common import ApiError, IG_USER_ID, call

POLL_SEC = 5
POLL_MAX = 60  # 최대 5분 (문서 권장 상한)


def check_url(url: str):
    r = requests.head(url, timeout=30, allow_redirects=True)
    ctype = r.headers.get("Content-Type", "")
    if r.status_code != 200 or "jpeg" not in ctype:
        sys.exit(f"[URL 오류] {url} -> HTTP {r.status_code}, Content-Type={ctype}")
    print(f"  URL OK  {url}  ({ctype}, {r.headers.get('Content-Length')} bytes)")


def wait_finished(container_id: str, label: str):
    for _ in range(POLL_MAX):
        st = call("GET", container_id, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise ApiError(f"{label} 컨테이너 {container_id} 상태={code} 상세={st.get('status')}")
        time.sleep(POLL_SEC)
    raise ApiError(f"{label} 컨테이너 {container_id} 처리 시간 초과")


def publish(urls: list[str], caption: str) -> dict:
    """캐러셀 게시 후 {media_id, permalink, media_type, timestamp} 반환. 실패 시 ApiError."""
    if not 2 <= len(urls) <= 20:
        raise ValueError("캐러셀은 2~20장이어야 합니다.")
    print("[1] 이미지별 컨테이너 생성")
    children = []
    for i, u in enumerate(urls, 1):
        cid = call("POST", f"{IG_USER_ID}/media", image_url=u, is_carousel_item="true")["id"]
        wait_finished(cid, f"아이템{i}")
        print(f"  아이템{i} 컨테이너 {cid} FINISHED")
        children.append(cid)

    print("[2] 캐러셀 컨테이너 생성")
    carousel = call("POST", f"{IG_USER_ID}/media", media_type="CAROUSEL",
                    children=",".join(children), caption=caption)["id"]
    wait_finished(carousel, "캐러셀")
    print(f"  캐러셀 컨테이너 {carousel} FINISHED")

    print("[3] media_publish")
    media_id = call("POST", f"{IG_USER_ID}/media_publish", creation_id=carousel)["id"]
    print(f"  게시 완료 media_id={media_id}")

    info = call("GET", media_id, fields="permalink,media_type,timestamp")
    print(f"[4] permalink={info.get('permalink')}  type={info.get('media_type')}  at={info.get('timestamp')}")
    return {"media_id": media_id, **{k: info.get(k) for k in ("permalink", "media_type", "timestamp")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--caption", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    print("[0] 이미지 URL 점검")
    for u in a.urls:
        check_url(u)
    if not a.dry_run:
        publish(a.urls, a.caption)


if __name__ == "__main__":
    try:
        main()
    except ApiError as e:
        print("[API 오류]\n" + str(e))
        sys.exit(1)
