"""
자연어 입력 핸들러 — Case 2 (AI 콘텐츠 생성 + 디자인 적용).

사용자의 자연어 요청을 Claude API에 보내서 슬라이드 JSON을 생성한 뒤
빌드 파이프라인에 태움.
"""
from __future__ import annotations
import json
import logging
import re
import time
from pathlib import Path

from slack_bot.ai.generator import generate_deck_json
from slack_bot.builder import build_and_publish

log = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """파일명에 쓸 수 있게 정리."""
    s = re.sub(r"[^\w\s가-힣]", "", text)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:60] or f"deck_{int(time.time())}"


def handle(client, channel: str, user: str, text: str,
           anthropic_api_key: str, github_token: str, github_repo: str):
    """자연어 → AI 콘텐츠 생성 → 빌드."""
    log.info(f"natural_language from <@{user}>: {text}")

    # 1) Claude API로 슬라이드 JSON 생성
    try:
        client.chat_postMessage(channel=channel,
            text=f"🤖 AI가 콘텐츠를 작성 중입니다... (보통 30~60초)")
        data = generate_deck_json(prompt=text, api_key=anthropic_api_key)
    except Exception as e:
        log.exception("AI generation failed")
        client.chat_postMessage(channel=channel,
            text=f"<@{user}> AI 생성 실패: `{e}`")
        return

    # 2) 빌드
    title = data.get("meta", {}).get("title", "deck")
    stem = _slugify(title)
    client.chat_postMessage(channel=channel,
        text=f"✏️ 콘텐츠 작성 완료. 디자인 적용 + 파일 생성 중... ⏳")

    try:
        result = build_and_publish(data=data, stem=stem,
                                   github_token=github_token,
                                   github_repo=github_repo)
    except Exception as e:
        log.exception("build failed")
        client.chat_postMessage(channel=channel,
            text=f"<@{user}> 빌드 실패: `{e}`")
        return

    # 3) 회신
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"<@{user}> 완성! ✨ *{title}*"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"📋 *원본 요청*\n> {text}"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"<{result['html_url']}|🌐 HTML 미리보기>"}},
        {"type": "context", "elements": [
            {"type": "mrkdwn",
             "text": f"📊 {result['slide_count']}장 · 🕒 {result['build_seconds']:.1f}초 · 🤖 AI 생성"}
        ]}
    ]
    client.chat_postMessage(channel=channel, blocks=blocks)

    for filepath, title_text in [(result["pptx_path"], "PPTX (편집용)"),
                                   (result["pdf_path"], "PDF (인쇄·공유용)")]:
        client.files_upload_v2(
            channel=channel, file=str(filepath),
            initial_comment=f"📎 {title_text}", title=Path(filepath).name)
