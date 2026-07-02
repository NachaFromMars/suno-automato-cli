#!/usr/bin/env bash
# ensure-xvfb.sh — start-or-reuse a single fixed Xvfb display instead of xvfb-run -a.
#
# Why: `xvfb-run -a` allocates a NEW display + /tmp/xvfb-run.XXXXXX dir on every
# call and leaks both when the wrapped process is killed (observed: 995 stale
# dirs / hundreds of leaked displays). This helper keeps ONE display (:99 by
# default) alive and reuses it, guarded by an flock so concurrent callers never
# race to start two servers.
#
# Usage:
#   source ensure-xvfb.sh          # exports DISPLAY (and starts Xvfb if needed)
#   ensure-xvfb.sh some-command…   # or run a command under the shared display
set -u

XVFB_DISPLAY="${XVFB_DISPLAY:-:99}"
XVFB_SCREEN="${XVFB_SCREEN:-1920x1080x24}"
XVFB_LOCK="${XVFB_LOCK:-/tmp/.ensure-xvfb.lock}"

ensure_xvfb() {
  if DISPLAY="$XVFB_DISPLAY" xdpyinfo >/dev/null 2>&1; then
    export DISPLAY="$XVFB_DISPLAY"
    return 0
  fi
  exec 8>"$XVFB_LOCK"
  flock 8
  # re-check under lock (someone else may have started it)
  if ! DISPLAY="$XVFB_DISPLAY" xdpyinfo >/dev/null 2>&1; then
    # clear a stale X lock file for this display if no server owns it
    num="${XVFB_DISPLAY#:}"
    if [ -e "/tmp/.X${num}-lock" ] && ! pgrep -f "Xvfb ${XVFB_DISPLAY}\b" >/dev/null 2>&1; then
      rm -f "/tmp/.X${num}-lock" "/tmp/.X11-unix/X${num}" 2>/dev/null
    fi
    nohup Xvfb "$XVFB_DISPLAY" -screen 0 "$XVFB_SCREEN" -nolisten tcp \
      >/dev/null 2>&1 &
    for _ in $(seq 1 25); do
      DISPLAY="$XVFB_DISPLAY" xdpyinfo >/dev/null 2>&1 && break
      sleep 0.2
    done
  fi
  flock -u 8
  exec 8>&-
  export DISPLAY="$XVFB_DISPLAY"
  DISPLAY="$XVFB_DISPLAY" xdpyinfo >/dev/null 2>&1
}

if [ "${BASH_SOURCE[0]:-}" = "${0:-}" ]; then
  # executed directly: ensure display, then exec the given command under it
  ensure_xvfb || { echo "ensure-xvfb: failed to start Xvfb $XVFB_DISPLAY" >&2; exit 1; }
  [ $# -gt 0 ] && exec "$@"
  echo "DISPLAY=$DISPLAY"
else
  ensure_xvfb
fi
