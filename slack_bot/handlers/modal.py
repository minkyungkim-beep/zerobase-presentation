"""
모달 폼 핸들러 — 정밀 입력.
"""
from __future__ import annotations
import logging
import re
import time
from pathlib import Path

from slack_bot.ai.generator import generate_deck_json
from slack_bot.builder import build_and_publish

log = logging.getLogger(__name__)


def open_modal(client, trigger_id: str):
    """모달 폼을 연다."""
    client.views_open(trigger_id=trigger_id, view={
        "type": "modal",
        "callback_id": "zerodeck_form_submit",
        "title": {"type": "plain_text", "text": "ZeroDeck 폼"},
        "submit": {"type": "plain_text", "text": "생성"},
        "close":  {"type": "plain_text", "text": "취소"},
        "blocks": [
            {"type": "input", "block_id": "topic_block",
             "label": {"type": "plain_text", "text": "주제"},
             "element": {"type": "plain_text_input", "action_id": "topic",
                         "placeholder": {"type": "plain_text",
                                         "text": "예: 자기소개서 작성법"}}},
            {"type": "input", "block_id": "audience_block",
             "label": {"type": "plain_text", "text": "대상 청중"},
             "element": {"type": "plain_text_input", "action_id": "audience",
                         "placeholder": {"type": "plain_text",
                                         "text": "예: 신입 취준생"}}},
            {"type": "input", "block_id": "slides_block",
             "label": {"type": "plain_text", "text": "슬라이드 수 (선택)"},
             "element": {"type": "plain_text_input", "action_id": "slides",
                         "placeholder": {"type": "plain_text", "text": "예: 8"}},
             "optional": True},
            {"type": "input", "block_id": "outline_block",
             "label": {"type": "plain_text", "text": "주요 챕터·내용 (선택)"},
             "element": {"type": "plain_text_input", "action_id": "outline",
                         "multiline": True,
                         "placeholder": {"type": "plain_text",
                                         "text": "예:\n1. 자소서의 3가지 핵심 요소\n2. 공채 vs 수시 차이\n3. 합격 사례"}},
             "optional": True},
            {"type": "input", "block_id": "tone_block",
             "label": {"type": "plain_text", "text": "톤"},
             "element": {"type": "static_select", "action_id": "tone",
                         "initial_option": {"value": "기본",
                            "text": {"type": "plain_text", "text": "기본 (컨설팅 톤)"}},
                         "options": [
                             {"value": "기본",
                              "text": {"type": "plain_text", "text": "기본 (컨설팅 톤)"}},
                             {"value": "친근",
                              "text": {"type": "plain_text", "text": "친근·대화체"}},
                             {"value": "공식",
                              "text": {"type": "plain_text", "text": "공식·격식"}}
                         ]}},
            {"type": "input", "block_id": "channel_block",
             "label": {"type": "plain_text", "text": "결과 받을 채널"},
             "element": {"type": "channels_select", "action_id": "channel",
                         "placeholder": {"type": "plain_text",
                                         "text": "채널 선택"}}},
        ],
    })


def _slugify(text: str) -> str:
    s = re.sub(r"[^\w\s가-힣]", "", text or "")
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:60] or f"deck_{int(time.time())}"


def handle_submit(client, body, view, anthropic_api_key: str,
                  github_token: str, github_repo: str):
    """모달 폼 제출 처리."""
    user_id = body["user"]["id"]
    values = view["state"]["values"]
    topic = values["topic_block"]["topic"]["value"]
    audience = values["audience_block"]["audience"]["value"]
    slides = values["slides_block"]["slides"].get("value") or "8"
    outline = values["outline_block"]["outline"].get("value") or ""
    tone = values["tone_block"]["tone"]["selected_option"]["value"]
    channel_id = values["channel_block"]["channel"]["selected_channel"]

    log.info(f"modal submit from <@{user_id}>: {topic} / {audience}")

    # 자연어 prompt로 합치기
    prompt = f"""주제: {topic}
대상: {audience}
슬라이드 수: {slides}
톤: {tone}
"""
    if outline:
        prompt += f"\n구성:\n{outline}"

    client.chat_postMessage(channel=channel_id,
        text=f"<@{user_id}> 폼 제출 받았어요 ✨ *{topic}*\n🤖 AI 작성 중...")

    try:
        data = generate_deck_json(prompt=prompt, api_key=anthropic_api_key)
        result = build_and_publish(data=data, stem=_slugify(topic),
                                   github_token=github_token,
                                   github_repo=github_repo)
    except Exception as e:
        log.exception("modal pipeline failed")
        client.chat_postMessage(channel=channel_id,
            text=f"<@{user_id}> 처리 실패: `{e}`")
        return

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"<@{user_id}> 완성 ✨ *{topic}*"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"<{result['html_url']}|🌐 HTML 미리보기>"}},
        {"type": "context", "elements": [
            {"type": "mrkdwn",
             "text": f"📊 {result['slide_count']}장 · 🕒 {result['build_seconds']:.1f}초"}
        ]}
    ]
    client.chat_postMessage(channel=channel_id, blocks=blocks)

    for filepath, title_text in [(result["pptx_path"], "PPTX (편집용)"),
                                   (result["pdf_path"], "PDF (인쇄·공유용)")]:
        client.files_upload_v2(
            channel=channel_id, file=str(filepath),
            initial_comment=f"📎 {title_text}", title=Path(filepath).name)
