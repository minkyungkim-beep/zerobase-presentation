"""
JSON 파일 업로드 핸들러 — Case 1 (디자인 자동화).

JSON 파일이 업로드되면 그대로 빌드 파이프라인에 태움.
"""
from __future__ import annotations
import json
import logging
import tempfile
from pathlib import Path
import requests

from slack_bot.builder import build_and_publish

log = logging.getLogger(__name__)


def handle(client, channel: str, user: str, file_info: dict,
           github_token: str, github_repo: str):
    """채널에 업로드된 JSON 파일을 받아 빌드."""
    name = file_info["name"]
    log.info(f"file_shared from <@{user}>: {name}")

    # JSON 파일 다운로드 (Slack은 인증 필요)
    url = file_info["url_private"]
    headers = {"Authorization": f"Bearer {client.token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        client.chat_postMessage(channel=channel,
            text=f"<@{user}> 파일을 다운로드 못 했어요 (HTTP {resp.status_code}).")
        return

    try:
        data = json.loads(resp.text)
    except json.JSONDecodeError as e:
        client.chat_postMessage(channel=channel,
            text=f"<@{user}> JSON 파싱 실패: {e}")
        return

    # 빌드 실행
    stem = Path(name).stem
    client.chat_postMessage(channel=channel,
        text=f"<@{user}> JSON 받았어요! `{name}` 빌드 시작합니다 ⏳")

    try:
        result = build_and_publish(data=data, stem=stem,
                                   github_token=github_token,
                                   github_repo=github_repo)
    except Exception as e:
        log.exception("build failed")
        client.chat_postMessage(channel=channel,
            text=f"<@{user}> 빌드 실패: `{e}`")
        return

    # 결과 회신
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"<@{user}> 완성되었습니다 ✨ *{stem}*"}},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"<{result['html_url']}|🌐 HTML 미리보기>"}},
        {"type": "context", "elements": [
            {"type": "mrkdwn",
             "text": f"📊 슬라이드 {result['slide_count']}장 · "
                     f"🕒 {result['build_seconds']:.1f}초"}
        ]}
    ]
    client.chat_postMessage(channel=channel, blocks=blocks)

    # PPTX·PDF 파일 첨부
    for filepath, title in [(result["pptx_path"], "PPTX (편집용)"),
                             (result["pdf_path"], "PDF (인쇄·공유용)")]:
        client.files_upload_v2(
            channel=channel, file=str(filepath),
            initial_comment=f"📎 {title}", title=Path(filepath).name)
