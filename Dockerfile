# syntax=docker/dockerfile:1

FROM python:3.14-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    POETRY_DYNAMIC_VERSIONING_BYPASS=0.0.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Custom nextcord fork required by the bot (see .github/workflows/ci.yml)
RUN git clone --depth 1 --branch components_v2 \
    https://github.com/alentoghostflame/nextcord.git /tmp/nextcord \
    && pip install --upgrade pip \
    && pip install /tmp/nextcord \
    && rm -rf /tmp/nextcord

WORKDIR /build
COPY requirements.txt .
RUN pip install -r requirements.txt


FROM python:3.14-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system bishokus \
    && useradd --system --create-home --gid bishokus bishokus

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --chown=bishokus:bishokus . .

RUN mkdir -p /app/config /app/.logs \
    && chown -R bishokus:bishokus /app

USER bishokus

# Required environment variables:
# - BOT_TOKEN: Discord bot token (sensitive)
# - DB_HOST: Database host (default: localhost)
# - DB_PORT: Database port (default: 3306)
# - DB_USER: Database user (default: bishokus)
# - DB_PASSWORD: Database password (sensitive)
# - DB_NAME: Database name (default: bishokus)
# Optional:
# - TEST_BOT_TOKEN: Test bot token for testing
# - OPENWEATHER_API_KEY: OpenWeather API key
# - BLAGUES_API_KEY: Blagues API key
# See .env.example and docs/CD.md for more details.
#
# System dependencies: ffmpeg

ENTRYPOINT ["python", "bot.py"]
