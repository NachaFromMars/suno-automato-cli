#!/usr/bin/env bash
set -uo pipefail
ROOT="/root/.openclaw/workspace/suno-automato-cli"
LOG="$ROOT/suno-library/run-to-complete-$(date +%Y%m%d-%H%M%S).log"
LOCK="$ROOT/suno-library/.run-to-complete.lock"

# F-04: single-instance lock — never run two batch loops concurrently.
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "[locked] another run-to-complete instance holds $LOCK; exiting" | tee -a "$LOG"
  exit 75
fi

export DISPLAY="${DISPLAY:-:99}"
# F-09: resolve the newest live xvfb-run Xauthority dynamically (survives reboots).
if [[ -z "${XAUTHORITY:-}" ]]; then
  XAUTH_NEWEST="$(ls -1t /tmp/xvfb-run.*/Xauthority 2>/dev/null | head -1 || true)"
  [[ -n "$XAUTH_NEWEST" ]] && export XAUTHORITY="$XAUTH_NEWEST"
fi
echo "[start] $(date -Is) DISPLAY=$DISPLAY XAUTHORITY=${XAUTHORITY:-unset}" | tee -a "$LOG"
for i in $(seq 1 60); do
  echo "[run $i] $(date -Is)" | tee -a "$LOG"
  timeout 1000 python3 "$ROOT/scripts/suno-batch-runner.py" >>"$LOG" 2>&1 || echo "[run $i] runner rc=$?" | tee -a "$LOG"
  timeout 120 python3 "$ROOT/scripts/suno-playlist-refresh.py" >>"$LOG" 2>&1 || true
  timeout 180 python3 "$ROOT/scripts/suno-remote-playlist-sync.py" >>"$LOG" 2>&1 || true
  rem=$(python3 - <<'PY'
import importlib.util, pathlib
root=pathlib.Path('/root/.openclaw/workspace/suno-automato-cli')
spec=importlib.util.spec_from_file_location('runner', root/'scripts/suno-batch-runner.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print(sum(max(0, mod.target_for_album(a['album'])-mod.album_track_count(a['album'])) for a in mod.PLAN))
PY
)
  echo "[remaining $i] $rem tracks" | tee -a "$LOG"
  [[ "$rem" == "0" ]] && { echo "[complete] $(date -Is)" | tee -a "$LOG"; exit 0; }
  sleep 3
done
echo "[stopped] max iterations" | tee -a "$LOG"; exit 1
