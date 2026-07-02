"""Central config for automato-server. No secrets stored in code.

Precedence (highest wins): environment variables > automato.toml > built-in defaults.

automato.toml search order:
  1. $AUTOMATO_CONFIG (explicit path)
  2. <repo>/automato.toml          (suno-automato-cli/automato.toml)
  3. <repo>/server/automato.toml
See automato.toml.example in the repo root for all keys.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

# Repo layout (server/ lives inside suno-automato-cli/)
SERVER_DIR = Path(__file__).resolve().parents[1]          # .../suno-automato-cli/server
REPO_ROOT = SERVER_DIR.parent                              # .../suno-automato-cli
WORKSPACE = REPO_ROOT.parent                               # .../workspace

VERSION = "1.0.0"


def _load_toml() -> dict:
    candidates: list[Path] = []
    explicit = os.environ.get("AUTOMATO_CONFIG")
    if explicit:
        candidates.append(Path(explicit))
    candidates += [REPO_ROOT / "automato.toml", SERVER_DIR / "automato.toml"]
    for p in candidates:
        try:
            if p.is_file():
                with open(p, "rb") as fh:
                    data = tomllib.load(fh)
                data["_config_file"] = str(p)
                return data
        except Exception:
            continue
    return {}


_TOML = _load_toml()
CONFIG_FILE = _TOML.get("_config_file", "")


def _cfg(env_key: str, toml_key: str, default):
    """env var > automato.toml > default."""
    v = os.environ.get(env_key)
    if v is not None and v != "":
        return v
    v = _TOML.get(toml_key)
    if v is not None:
        return v
    return default


LIBRARY_ROOT = Path(_cfg("AUTOMATO_LIBRARY_ROOT", "library_root", REPO_ROOT / "suno-library"))
ALBUMS_ROOT = LIBRARY_ROOT / "_albums"
QUARANTINE_DIR = LIBRARY_ROOT / "_quarantine"
NOVELTY_HISTORY = LIBRARY_ROOT / "novelty-history.json"
BATCH_STATE = LIBRARY_ROOT / "batch-state.json"
INDEX_JSON = LIBRARY_ROOT / "index.json"
LYRICS_DIR = LIBRARY_ROOT / "_batch-lyrics"

# Same flock file as the CLI batch runner (F-04): server worker and CLI runner
# can never generate concurrently.
LOCK_FILE = LIBRARY_ROOT / ".batch-runner.lock"

SCRIPTS_DIR = REPO_ROOT / "scripts"
SUNO_LIB = SCRIPTS_DIR / "suno-lib.sh"
CHROME_WRAPPER = SCRIPTS_DIR / "chrome-for-suno.sh"

# Guard resolution: env/toml override > vendored copy in this repo > sibling suno-cli checkout.
_VENDORED_GUARD = SCRIPTS_DIR / "suno_prompt_guard.py"
_SIBLING_GUARD = WORKSPACE / "suno-cli" / "scripts" / "suno_prompt_guard.py"
PROMPT_GUARD = Path(_cfg("AUTOMATO_PROMPT_GUARD", "prompt_guard",
                         _VENDORED_GUARD if _VENDORED_GUARD.exists() else _SIBLING_GUARD))

SUNO_BIN = Path(_cfg("SUNO_BIN", "suno_bin", WORKSPACE / "bin" / "suno"))

# Server state (SQLite WAL queue/jobs db)
STATE_DIR = Path(_cfg("AUTOMATO_STATE_DIR", "state_dir", SERVER_DIR / "state"))
DB_PATH = STATE_DIR / "app.db"

HOST = str(_cfg("AUTOMATO_HOST", "host", "127.0.0.1"))
PORT = int(_cfg("AUTOMATO_PORT", "port", 8765))

# Optional bearer token. When set, mutating endpoints (generate, cancel,
# worker pause/resume, /ui/generate) and the /mcp mount require
# `Authorization: Bearer <token>`. Empty/unset = auth disabled (loopback default).
API_TOKEN = str(_cfg("AUTOMATO_API_TOKEN", "api_token", "") or "")

# Safety limits
MAX_GENERATIONS_PER_DAY = int(_cfg("AUTOMATO_MAX_GEN_PER_DAY", "max_generations_per_day", 40))
GUARD_TIMEOUT = 45
GENERATE_TIMEOUT = 900
PROBE_TIMEOUT = 60

INSTRUMENTAL_GENRES = {"Instrumental", "Relax-Sleep", "Restaurant-Jazz-Instrument"}

# Novelty thresholds mirror the batch runner values
NOVELTY_THRESHOLD_VOCAL = "0.34"
NOVELTY_THRESHOLD_INSTRUMENTAL = "0.62"

def safe_config() -> dict:
    """Config subset safe to expose over the API — paths only, never secrets."""
    return {
        "version": VERSION,
        "config_file": CONFIG_FILE or None,
        "repo_root": str(REPO_ROOT),
        "library_root": str(LIBRARY_ROOT),
        "albums_root": str(ALBUMS_ROOT),
        "prompt_guard": str(PROMPT_GUARD),
        "suno_bin": str(SUNO_BIN),
        "lock_file": str(LOCK_FILE),
        "db_path": str(DB_PATH),
        "host": HOST,
        "port": PORT,
        "api_token_set": bool(API_TOKEN),
        "max_generations_per_day": MAX_GENERATIONS_PER_DAY,
        "instrumental_genres": sorted(INSTRUMENTAL_GENRES),
        "novelty_threshold_vocal": NOVELTY_THRESHOLD_VOCAL,
        "novelty_threshold_instrumental": NOVELTY_THRESHOLD_INSTRUMENTAL,
        "auth_file_note": "auth.json stays in ~/.config/suno-cli/ (0600), read by the suno CLI only; never exposed here.",
    }
