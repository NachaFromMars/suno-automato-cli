# Suno Automato — single-image server (FastAPI + worker + MCP + dashboard)
#
# The image ships the server + guard scripts + Xvfb (needed by the captcha
# solver's piloted Chrome). The `suno` CLI binary and your auth.json are NOT
# baked in — mount them (see docker-compose.yml).
FROM python:3.12-slim-trixie

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# Xvfb + chromium (captcha solver pilots a real Chrome under X).
# `chromium` pulls in the full browser runtime dependency set.
RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb xauth x11-utils \
        chromium \
        fonts-liberation fonts-noto-color-emoji fonts-noto-cjk \
        ca-certificates curl jq procps util-linux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY server/requirements.txt server/requirements.txt
RUN pip install -r server/requirements.txt

COPY scripts/ scripts/
COPY server/automato/ server/automato/
COPY automato.toml.example docker-entrypoint.sh LICENSE README.md ./
RUN chmod +x docker-entrypoint.sh scripts/*.sh 2>/dev/null || true

# Defaults for the container layout (all overridable via env / automato.toml)
ENV AUTOMATO_HOST=0.0.0.0 \
    AUTOMATO_PORT=8765 \
    AUTOMATO_LIBRARY_ROOT=/data/suno-library \
    AUTOMATO_STATE_DIR=/data/state \
    AUTOMATO_PROMPT_GUARD=/app/scripts/suno_prompt_guard.py \
    SUNO_BIN=/app/bin/suno \
    DISPLAY=:99 \
    XAUTHORITY=/data/state/Xauthority

VOLUME ["/data/suno-library", "/data/state"]
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl -fsS http://127.0.0.1:8765/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
