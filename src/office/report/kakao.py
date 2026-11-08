"""카카오톡 '나에게 보내기' 보고.

카카오 개발자 앱에서 '카카오톡 메시지' 권한(talk_message)에 동의한 본인 계정의
액세스 토큰이 필요하다: 환경변수 KAKAO_ACCESS_TOKEN.
토큰이 없으면 보내지 않고 텍스트만 반환한다(dry-run).
승인은 카톡이 아니라 대시보드에서 버전 해시 기준으로 한다(헌장 4장).
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


def card_text(title: str, lines: list[str], packet_hash: str = "") -> str:
    body = "\n".join(f"· {l}" for l in lines)
    tail = f"\n버전 {packet_hash[7:19]}" if packet_hash else ""
    text = f"[{title}]\n{body}{tail}"
    return text[:200]   # 텍스트 템플릿 길이 제한 대비


def send(text: str, link_url: str = "") -> dict:
    token = os.getenv("KAKAO_ACCESS_TOKEN")
    if not token:
        return {"sent": False, "dry_run": True, "text": text}
    template = {"object_type": "text", "text": text,
                "link": {"web_url": link_url, "mobile_web_url": link_url}, "button_title": "대시보드에서 확인"}
    data = urllib.parse.urlencode({"template_object": json.dumps(template, ensure_ascii=False)}).encode()
    req = urllib.request.Request(MEMO_URL, data=data, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return {"sent": True, "response": json.loads(r.read())}
