"""Instagram Graph API 공통 유틸.

- 토큰/ID는 환경변수에서만 읽는다 (프로세스 환경 → Windows 사용자 환경변수 순).
- 모든 출력·예외 메시지에서 토큰 값을 마스킹한다.
"""
import json
import os
import sys

import requests

# 시스템 사용자 토큰(EAA...) + instagram_content_publish = Facebook Login 계열 → graph.facebook.com
API_HOST = "https://graph.facebook.com"
API_VERSION = "v27.0"
BASE = f"{API_HOST}/{API_VERSION}"


def _env(name: str) -> str:
    val = os.environ.get(name)
    if not val and sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                val, _ = winreg.QueryValueEx(k, name)
        except OSError:
            val = None
    if not val:
        sys.exit(f"[오류] 환경변수 {name} 가 설정되지 않았습니다.")
    return val


TOKEN = _env("IG_ACCESS_TOKEN")
IG_USER_ID = _env("IG_USER_ID")


def mask(text: str) -> str:
    return str(text).replace(TOKEN, "***TOKEN***")


class ApiError(Exception):
    pass


def call(method: str, path: str, **params) -> dict:
    """Graph API 호출. 토큰은 Authorization 헤더로 보내 URL/로그에 남지 않게 한다."""
    url = f"{BASE}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if method == "GET":
        r = requests.get(url, params=params, headers=headers, timeout=60)
    else:
        r = requests.post(url, data=params, headers=headers, timeout=120)
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text}
    if r.status_code != 200 or "error" in body:
        raise ApiError(
            mask(f"{method} {path} -> HTTP {r.status_code}\n"
                 + json.dumps(body, ensure_ascii=False, indent=2))
        )
    return body
