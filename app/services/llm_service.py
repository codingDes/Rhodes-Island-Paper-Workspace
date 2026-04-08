from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from app.config import Settings


def chat_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    settings = Settings.load()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is empty.")

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Some OpenAI-compatible providers may ignore response_format.
        # Try to extract the first JSON object from plain text response.
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            raise ValueError(f"Model response is not valid JSON: {content[:240]}")
        return json.loads(match.group(0))


def chat_text(system_prompt: str, user_prompt: str) -> str:
    settings = Settings.load()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is empty.")

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
    return (resp.choices[0].message.content or "").strip()

