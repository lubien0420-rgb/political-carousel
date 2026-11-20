"""토큰/계정/호스트 확인 (게시 없음)."""
import sys

from ig_common import ApiError, BASE, IG_USER_ID, call

try:
    me = call("GET", IG_USER_ID, fields="id,username,media_count")
    print(f"[OK] host={BASE}")
    print(f"     username={me.get('username')} media_count={me.get('media_count')}")
    lim = call("GET", f"{IG_USER_ID}/content_publishing_limit", fields="config,quota_usage")
    print(f"     publishing_limit={lim.get('data')}")
except ApiError as e:
    print("[실패]\n" + str(e))
    sys.exit(1)
