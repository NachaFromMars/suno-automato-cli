#!/usr/bin/env bash
set -euo pipefail

SUNO_BIN="${SUNO_BIN:-/root/.openclaw/workspace/bin/suno}"

if [[ ! -x "$SUNO_BIN" ]]; then
  echo "suno binary not found or not executable: $SUNO_BIN" >&2
  exit 127
fi

cmd="${1:-}"
if [[ -z "$cmd" ]]; then
  cat >&2 <<USAGE
Usage:
  $0 credits
  $0 models
  $0 list [args...]
  $0 refresh
  $0 generate [suno generate args...]
  $0 download [suno download args...]
USAGE
  exit 2
fi
shift || true

case "$cmd" in
  credits)
    exec "$SUNO_BIN" credits --json "$@"
    ;;
  models)
    exec "$SUNO_BIN" models --json "$@"
    ;;
  list)
    exec "$SUNO_BIN" list --json "$@"
    ;;
  refresh)
    exec "$SUNO_BIN" auth --refresh --json "$@"
    ;;
  generate)
    echo "[suno-safe] generation may spend credits" >&2
    exec "$SUNO_BIN" generate "$@"
    ;;
  download)
    exec "$SUNO_BIN" download "$@"
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    exit 2
    ;;
esac
