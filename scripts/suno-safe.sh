#!/usr/bin/env bash
set -euo pipefail

SUNO_BIN="${SUNO_BIN:-/root/.openclaw/workspace/bin/suno}"

if [[ ! -x "$SUNO_BIN" ]]; then
  echo "suno binary not found or not executable: $SUNO_BIN" >&2
  exit 127
fi

# F-10: 'generate' spends credits; require the gated-caller marker or explicit override.
if [[ "${1:-}" == "generate" && "${AUTOMATO_GATED:-}" != "1" ]]; then
  force=0
  newargs=()
  for a in "$@"; do
    if [[ "$a" == "--force-ungated" ]]; then force=1; else newargs+=("$a"); fi
  done
  if [[ $force -ne 1 ]]; then
    echo "[suno-safe GUARD] REFUSED: ungated 'generate' (bypasses prompt-guard gate, spends credits)." >&2
    echo "[suno-safe GUARD] Use automato-server / suno-batch-runner.py, or pass --force-ungated to accept the risk." >&2
    exit 78
  fi
  echo "[suno-safe GUARD] *** WARNING: --force-ungated — generating WITHOUT the strict guard gate. ***" >&2
  export AUTOMATO_GATED=1
  set -- "${newargs[@]}"
fi

cmd="${1:-}"
if [[ -z "$cmd" ]]; then
  cat >&2 <<USAGE
Usage:
  $0 auth [args...]
  $0 refresh
  $0 credits
  $0 models
  $0 list [args...]
  $0 search <query> [args...]
  $0 info <clip_id> [args...]
  $0 status [clip_ids...] [args...]
  $0 persona <persona_id> [args...]
  $0 timed-lyrics <clip_id> [args...]
  $0 lyrics [args...]
  $0 describe [args...]
  $0 generate [args...]
  $0 extend [args...]
  $0 concat [args...]
  $0 cover [args...]
  $0 remaster [args...]
  $0 stems [args...]
  $0 download [args...]
  $0 set [args...]
  $0 publish [args...]
  $0 delete [args...]
  $0 config [args...]
  $0 agent-info
  $0 update [args...]
USAGE
  exit 2
fi
shift || true

case "$cmd" in
  refresh)
    exec "$SUNO_BIN" auth --refresh --json "$@"
    ;;
  credits|models|list|search|info|status|persona|timed-lyrics|lyrics|describe|generate|extend|concat|cover|remaster|stems|download|set|publish|delete|config|auth|agent-info|install-skill|update)
    case "$cmd" in
      generate|describe|extend|concat|cover|remaster|stems)
        echo "[suno-safe] creation command may spend credits: $cmd" >&2
        ;;
      delete)
        echo "[suno-safe] destructive command: delete" >&2
        ;;
      set|publish)
        echo "[suno-safe] mutating command: $cmd" >&2
        ;;
    esac
    exec "$SUNO_BIN" "$cmd" "$@"
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    exit 2
    ;;
esac
