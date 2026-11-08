"""세 AI API 호출. 표준 라이브러리만 사용한다.

모델명은 환경변수로 정한다(모델은 빠르게 바뀌므로 코드에 고정하지 않음, 헌장 11장).
  OPENAI_API_KEY, OPENAI_MODEL
  ANTHROPIC_API_KEY, ANTHROPIC_MODEL
  GEMINI_API_KEY, GEMINI_MODEL
"""
from __future__ import annotations

import json
import os
import urllib.request

TIMEOUT = 120
MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "4000"))
TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.2"))   # 세 AI 동일 설정(헌장 4장)


def _post(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def _parse(text: str) -> dict:
    """양식 밖 텍스트는 버리고 JSON 객체만 취한다(헌장 5장)."""
    s, e = text.find("{"), text.rfind("}")
    if s < 0 or e < 0:
        return {"claims": [], "error": "JSON 없음"}
    try:
        return json.loads(text[s:e + 1])
    except json.JSONDecodeError:
        return {"claims": [], "error": "JSON 파싱 실패"}


def call(name: str, system: str, prompt: str) -> dict:
    if name == "gpt":
        r = _post("https://api.openai.com/v1/chat/completions",
                  {"authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                  {"model": os.environ["OPENAI_MODEL"], "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
                   "response_format": {"type": "json_object"},
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
        return _parse(r["choices"][0]["message"]["content"])
    if name == "claude":
        r = _post("https://api.anthropic.com/v1/messages",
                  {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
                  {"model": os.environ["ANTHROPIC_MODEL"], "max_tokens": MAX_TOKENS, "temperature": TEMPERATURE,
                   "system": system, "messages": [{"role": "user", "content": prompt}]})
        return _parse("".join(b.get("text", "") for b in r["content"]))
    if name == "gemini":
        model = os.environ["GEMINI_MODEL"]
        r = _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                  {"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                  {"systemInstruction": {"parts": [{"text": system}]},
                   "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": TEMPERATURE, "maxOutputTokens": MAX_TOKENS,
                                        "responseMimeType": "application/json"}})
        return _parse(r["candidates"][0]["content"]["parts"][0]["text"])
    raise ValueError(name)


def mock_call(name: str, system: str, prompt: str) -> dict:
    """API 키 없이 흐름을 시험하는 가짜 응답."""
    cross = "다른 검토자의 답변" in prompt
    base = {
        "summary": f"{name} 모의 검토",
        "claims": [{"id": "C1", "statement": "현재 낙폭은 경고선(10%) 미만이다",
                    "evidence": {"type": "query", "ref": "facts.summary",
                                 "check": {"path": "facts.summary.drawdown", "op": "<", "value": 0.10}},
                    "confidence": 0.9, "severity": "major"}],
        "objections_to_others": [],
        "unverified": [],
        "charter_check": {"honest_and_lawful": True, "no_exploitation": True, "confidentiality_kept": True},
    }
    if cross:
        base["objections_to_others"] = [{"target": "A.C1", "verdict": "동의", "reason": "모의"}]
    return base
