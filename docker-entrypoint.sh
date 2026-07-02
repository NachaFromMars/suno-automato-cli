#!/usr/bin/env bash
# Container entrypoint: fixed Xvfb display + fixed Xauthority, then the server.
set -euo pipefail

DISPLAY="${DISPLAY:-:99}"
XAUTHORITY="${XAUTHORITY:-/data/state/Xauthority}"
export DISPLAY XAUTHORITY

mkdir -p "$(dirname "$XAUTHORITY")"

# Fixed Xauthority (no xvfb-run temp dirs → nothing to leak).
# Regenerated on every start: xauth cookies are keyed by hostname and each
# container run gets a new hostname, so a reused volume would carry a stale entry.
rm -f "$XAUTHORITY"
touch "$XAUTHORITY"
xauth -f "$XAUTHORITY" add "$(hostname)/unix:${DISPLAY#:}" MIT-MAGIC-COOKIE-1 \
  "$(head -c16 /dev/urandom | od -An -tx1 | tr -d ' \n')"

num="${DISPLAY#:}"
rm -f "/tmp/.X${num}-lock" "/tmp/.X11-unix/X${num}" 2>/dev/null || true
Xvfb "$DISPLAY" -screen 0 "${XVFB_SCREEN:-1920x1080x24}" -nolisten tcp -auth "$XAUTHORITY" &
XVFB_PID=$!

for _ in $(seq 1 50); do
  xdpyinfo >/dev/null 2>&1 && break
  sleep 0.2
done
xdpyinfo >/dev/null 2>&1 || { echo "FATAL: Xvfb $DISPLAY failed to start" >&2; exit 1; }
echo "Xvfb up on $DISPLAY (pid $XVFB_PID, auth $XAUTHORITY)"

trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT

cd /app/server
exec python -m uvicorn automato.server:app \
  --host "${AUTOMATO_HOST:-0.0.0.0}" --port "${AUTOMATO_PORT:-8765}"
