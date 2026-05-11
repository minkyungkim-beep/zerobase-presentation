"""
AI 콘텐츠 생성 — Claude API로 슬라이드 JSON 생성.

자연어 프롬프트를 받아서 디자인 시스템 v1.4 스키마에 맞는 JSON 반환.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path

import anthropic

log = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompt_template.md"


def generate_deck_json(prompt: str, api_key: str) -> dict:
    """자연어 → JSON 슬라이드 데이터."""
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text
    # ```json ... ``` 블록 추출 (Claude가 마크다운으로 감쌀 때)
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    data = json.loads(text.strip())
    log.info(f"AI generated {len(data.get('slides', []))} slides")
    return data
