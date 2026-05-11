"""
ZeroBase Deck Bot — Slack Bolt 메인 라우터.

지원 입력 방식 (4종):
  1) /제로덱 [자연어]        — 슬래시 커맨드
  2) @ZeroDeck 멘션         — 자연어 대화
  3) /제로덱-폼              — 모달 폼
  4) JSON 파일 업로드        — 파일 + 멘션
"""
from __future__ import annotations
import os
import sys
import json
import logging
from pathlib import Path

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

# 우리 프로젝트의 빌드 파이프라인
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import build_pptx  # noqa: E402
import render_html  # noqa: E402
from slack_bot.handlers import file_upload, modal, natural_language  # noqa: E402

# ─────────────────────────────────────────────────────────────
# 환경 변수
# ─────────────────────────────────────────────────────────────
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "minkyungkim-beep/zerobase-presentation")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Bolt + Flask 앱 초기화
# ─────────────────────────────────────────────────────────────
bolt = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
flask_app = Flask(__name__)
slack_handler = SlackRequestHandler(bolt)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """모든 Slack 이벤트(슬래시·멘션·파일·인터랙션)의 단일 진입점."""
    return slack_handler.handle(request)


@flask_app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "version": "0.1.0"}


# ─────────────────────────────────────────────────────────────
# 1) 슬래시 커맨드 — /제로덱
# ─────────────────────────────────────────────────────────────
@bolt.command("/제로덱")
def handle_command(ack, body, say, client):
    ack()  # 3초 안에 ack 필수
    user_id = body["user_id"]
    text = body.get("text", "").strip()
    channel_id = body["channel_id"]

    if not text:
        say(text="사용법: `/제로덱 자기소개서 작성법, 신입 취준생 대상, 8장`",
            channel=channel_id)
        return

    say(text=f"<@{user_id}> 요청 받았어요 ✨ 1~3분 안에 결과 드릴게요!\n> {text}",
        channel=channel_id)
    natural_language.handle(client=client, channel=channel_id, user=user_id,
                            text=text, anthropic_api_key=ANTHROPIC_API_KEY,
                            github_token=GITHUB_TOKEN, github_repo=GITHUB_REPO)


# ─────────────────────────────────────────────────────────────
# 2) 앱 멘션 — @ZeroDeck
# ─────────────────────────────────────────────────────────────
@bolt.event("app_mention")
def handle_mention(event, say, client):
    user_id = event["user"]
    text = event.get("text", "")
    # @ZeroDeck 부분 제거
    text = text.split(">", 1)[-1].strip() if ">" in text else text
    channel_id = event["channel"]

    if not text:
        say(text=f"<@{user_id}> 무엇을 도와드릴까요?\n"
                 f"• 자연어 요청 — `자기소개서 8장 만들어줘`\n"
                 f"• 폼 입력 — `/제로덱-폼`\n"
                 f"• JSON 파일 — 파일 첨부 후 저를 멘션해주세요",
            channel=channel_id)
        return

    say(text=f"<@{user_id}> 진행할게요 ✨", channel=channel_id)
    natural_language.handle(client=client, channel=channel_id, user=user_id,
                            text=text, anthropic_api_key=ANTHROPIC_API_KEY,
                            github_token=GITHUB_TOKEN, github_repo=GITHUB_REPO)


# ─────────────────────────────────────────────────────────────
# 3) 모달 폼 — /제로덱-폼
# ─────────────────────────────────────────────────────────────
@bolt.command("/제로덱-폼")
def handle_modal_command(ack, body, client):
    ack()
    modal.open_modal(client=client, trigger_id=body["trigger_id"])


@bolt.view("zerodeck_form_submit")
def handle_modal_submit(ack, body, view, client):
    ack()
    modal.handle_submit(client=client, body=body, view=view,
                        anthropic_api_key=ANTHROPIC_API_KEY,
                        github_token=GITHUB_TOKEN, github_repo=GITHUB_REPO)


# ─────────────────────────────────────────────────────────────
# 4) JSON 파일 업로드 — file_shared 이벤트
# ─────────────────────────────────────────────────────────────
@bolt.event("file_shared")
def handle_file_shared(event, client):
    file_id = event["file_id"]
    user_id = event["user_id"]
    info = client.files_info(file=file_id)["file"]
    if not info["name"].endswith(".json"):
        return  # JSON만 처리
    channels = info.get("channels", []) + info.get("groups", []) + info.get("ims", [])
    if not channels:
        return
    channel_id = channels[0]
    file_upload.handle(client=client, channel=channel_id, user=user_id,
                       file_info=info, github_token=GITHUB_TOKEN,
                       github_repo=GITHUB_REPO)


# ─────────────────────────────────────────────────────────────
# 5) 도움말 — /제로덱-도움말
# ─────────────────────────────────────────────────────────────
@bolt.command("/제로덱-도움말")
def handle_help(ack, body, say):
    ack()
    say(text=(
        "*ZeroDeck 사용법* 🎨\n"
        "\n"
        "*1) 자연어로 빠르게*\n"
        "`/제로덱 자기소개서 작성법, 신입 취준생, 8장`\n"
        "\n"
        "*2) 대화형으로*\n"
        "`@ZeroDeck 자기소개서 자료 만들어줘`\n"
        "\n"
        "*3) 폼으로 정밀 입력*\n"
        "`/제로덱-폼`\n"
        "\n"
        "*4) JSON 파일로 (개발자용)*\n"
        "JSON 파일을 채널에 업로드하면 자동 빌드\n"
        "\n"
        "*결과물*\n"
        "• HTML 미리보기 링크\n"
        "• PPTX 파일 (편집 가능)\n"
        "• PDF 파일 (인쇄용)\n"
        "\n"
        "_v0.1 · ZeroBase Design System v1.4 기반_"
    ))


# ─────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    log.info(f"Starting ZeroDeck bot on port {port}")
    flask_app.run(host="0.0.0.0", port=port)
