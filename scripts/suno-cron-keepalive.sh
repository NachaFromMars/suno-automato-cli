#!/usr/bin/env bash
# Suno batch keep-alive (called by Haiku cron every 20 min).
# 1) Check Suno web login state.
# 2) If logged IN  -> run one batch-runner step (continue generating).
# 3) If logged OUT -> (re)start the forever login keeper to restore the session,
#                     emit LOGIN_LOST so the agent can flag captcha if needed.
#
# Prints a compact JSON status line for the cron agent to read.
set -uo pipefail

ROOT="/root/.openclaw/workspace/suno-automato-cli"
WS="/root/.openclaw/workspace"
SCRIPTS="$ROOT/scripts"
LOG="$WS/suno-cron-keepalive.log"
STAMP="$(date '+%F %T %Z')"

log() { echo "[$STAMP] $*" >>"$LOG"; }

# --- 1. Login check -------------------------------------------------------
CHK="$(cd "$WS" && timeout 120 python3 "$SCRIPTS/suno-web-login-check.py" 2>>"$LOG")"
LOGGED_OUT="$(printf '%s' "$CHK" | python3 -c 'import sys,json;
try:
    d=json.load(sys.stdin); print("1" if d.get("logged_out") else "0")
except Exception:
    print("unknown")' 2>/dev/null)"

if [ "$LOGGED_OUT" = "0" ]; then
  # --- 2. Logged in -> continue batch ------------------------------------
  log "login OK -> running batch step"
  OUT="$(cd "$ROOT" && timeout 1200 python3 "$SCRIPTS/suno-batch-runner.py" 2>>"$LOG")"
  STATUS="$(printf '%s' "$OUT" | python3 -c 'import sys,json;
try:
    d=json.load(sys.stdin); print(d.get("status","?"))
except Exception:
    print("?")' 2>/dev/null)"
  log "batch step status=$STATUS"
  echo "{\"login\":\"ok\",\"action\":\"batch_step\",\"batch_status\":\"$STATUS\"}"
  exit 0
fi

if [ "$LOGGED_OUT" = "1" ]; then
  # --- 3. Logged out -> restart forever keeper to restore session --------
  log "LOGIN_LOST -> (re)starting forever keeper"
  if ! pgrep -f "suno_controller_forever.py" >/dev/null 2>&1; then
    [ -p "$WS/.suno_ctrl_fifo" ] || mkfifo "$WS/.suno_ctrl_fifo" 2>/dev/null
    nohup bash "$WS/suno-forever-keeper.sh" >>"$LOG" 2>&1 &
    log "forever keeper launched (pid $!)"
    KEEPER="started"
  else
    log "forever keeper already running"
    KEEPER="already_running"
  fi
  echo "{\"login\":\"lost\",\"action\":\"restart_login_keeper\",\"keeper\":\"$KEEPER\",\"note\":\"captcha_may_need_human\"}"
  exit 0
fi

# --- Unknown / check failed ----------------------------------------------
log "login check UNKNOWN; raw=$(printf '%s' "$CHK" | head -c 300)"
echo "{\"login\":\"unknown\",\"action\":\"none\",\"note\":\"login_check_failed\"}"
exit 0
