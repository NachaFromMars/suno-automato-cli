#!/usr/bin/env bash
set -uo pipefail
ROOT="/root/.openclaw/workspace/suno-automato-cli"
LOG="$ROOT/suno-library/run-to-complete-$(date +%Y%m%d-%H%M%S).log"
export DISPLAY="${DISPLAY:-:99}"
export XAUTHORITY="${XAUTHORITY:-/tmp/xvfb-run.cdSws5/Xauthority}"
echo "[start] $(date -Is) DISPLAY=$DISPLAY" | tee -a "$LOG"
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
