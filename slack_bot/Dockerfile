FROM python:3.11-slim

# 시스템 패키지 (Playwright 의존성 + 한글 폰트 + git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates curl \
    fonts-noto-cjk \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Pretendard 폰트 설치 (npm 경로)
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && cd /tmp && npm init -y && npm install pretendard@1.3.9 \
    && mkdir -p /usr/share/fonts/truetype/pretendard \
    && cp /tmp/node_modules/pretendard/dist/public/static/*.otf /usr/share/fonts/truetype/pretendard/ \
    && fc-cache -fv \
    && apt-get purge -y nodejs npm && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/node_modules

WORKDIR /app

# Python 의존성
COPY slack_bot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Playwright Chromium
RUN playwright install --with-deps chromium

# 프로젝트 전체 복사 (scripts, design_system, slack_bot 등)
COPY . /app/

# Cloud Run에서 PORT 환경 변수를 주입
ENV PORT=8080
EXPOSE 8080

# Gunicorn으로 Flask 앱 서빙
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 \
    --timeout 600 --worker-class gthread \
    slack_bot.app:flask_app
