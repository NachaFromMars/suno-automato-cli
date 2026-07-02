#!/usr/bin/env bash
set -euo pipefail

# F-10: 'generate' spends credits and used to bypass the strict guard gate.
# Gated callers (suno-batch-runner.py, automato-server engine) set AUTOMATO_GATED=1
# after running the full prompt-guard pipeline. Direct human/agent invocations must
# either go through the server/runner or explicitly accept the risk with --force-ungated.
if [[ "${1:-}" == "generate" && "${AUTOMATO_GATED:-}" != "1" ]]; then
  force=0
  args=()
  for a in "$@"; do
    if [[ "$a" == "--force-ungated" ]]; then force=1; else args+=("$a"); fi
  done
  if [[ $force -ne 1 ]]; then
    cat >&2 <<'EOF'
[suno-lib GUARD] REFUSED: direct 'generate' bypasses the strict prompt-guard gate
(precheck 11-block, lyrics-check, playlist-route, novelty-check) and SPENDS CREDITS.

Use one of:
  - automato-server API/UI/MCP (gated):   POST http://127.0.0.1:8765/api/v1/generate
  - batch runner (gated):                 scripts/suno-batch-runner.py
  - or accept the risk explicitly:        suno-lib.sh generate --force-ungated ...
EOF
    exit 78
  fi
  echo "[suno-lib GUARD] *** WARNING: --force-ungated — generating WITHOUT the strict guard gate. Credits will be spent on an unaudited prompt. ***" >&2
  export AUTOMATO_GATED=1
  exec "$(dirname "$0")/suno-lib.py" "${args[@]}"
fi
exec "$(dirname "$0")/suno-lib.py" "$@"
