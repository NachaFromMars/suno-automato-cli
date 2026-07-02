# The Guard Pipeline — PromptStyle contract, gates, exit codes

`scripts/suno_prompt_guard.py` (vendored from the sibling
[`suno-cli`](https://github.com/NachaFromMars/suno-cli) repo) is the single source of
truth for prompt quality. Every generation path — batch runner, server, MCP — runs it
**before** credits are spent (pre-gates) and **after** generation (postcheck).

## The 11-block PromptStyle contract

A style prompt must contain **all 11 labeled blocks**, in any order:

| # | Block | Purpose |
|---|---|---|
| 1 | `Leading Genre DNA` | primary genre + era/scene anchors |
| 2 | `Singer Identity` | voice persona (age, character, language) |
| 3 | `Vocal Register` | range, delivery, texture |
| 4 | `Rhythm Section` | drums/bass groove definition |
| 5 | `Signature Motif` | the ONE memorable instrumental hook |
| 6 | `Hook Design` | how the chorus/hook is constructed |
| 7 | `Arrangement Map` | section-by-section energy curve |
| 8 | `Instrument Palette` | concrete instruments (mic'd/played how) |
| 9 | `Mood Logic` | emotional arc |
| 10 | `Mix Target` | production/mix reference |
| 11 | `Strictly Avoid` | negative constraints |

On top of block presence, **production-detail density** is enforced: the prompt must be
concrete (instruments, techniques, references), not generic tag soup. Because Suno's
`tags` field caps at ~1000 chars, prompts are *compressed structured prompts* — short
labeled blocks, never bare tag lists.

## Pre-generation gates (all four must PASS)

| Gate | Subcommand | Checks |
|---|---|---|
| **Precheck** | `precheck --text <style>` | 11 blocks + density + length ≤1000 |
| **Lyrics check** | `lyrics-check --file <lyrics> --title <t> [--instrumental]` | section tags (`[Verse]`, `[Chorus]`…), hook presence, length, language/diacritics integrity; `--instrumental` switches to structure-map mode for no-vocal genres |
| **Playlist route** | `playlist-route --title <t> --text <style> --playlist <album> --albums-root <dir> --expect-genre <g>` | target album manifest exists and its genre matches |
| **Novelty check** | `novelty-check --title <t> --style <s> --lyrics-file <f> --history novelty-history.json --threshold <0.34\|0.62>` | whole-song similarity vs history, line-pattern (keyword-class) repetition, motif-window vs the 10 most recent songs |

Novelty thresholds: `0.34` vocal, `0.62` instrumental (instrumental styles legitimately
share more vocabulary).

## Postcheck (after generation)

```
suno_prompt_guard.py postcheck <clip_id> [<clip_id>…]
```

Fetches the **real clip metadata from Suno** (`suno info <id> --json`) and verifies the
stored tags/prompt still carry the 11-block structure (nothing was truncated or mangled
at submit time). Failure ⇒ the takes are moved to `suno-library/_quarantine/`, stripped
from the project's `takes`, and excluded from album track counts.

## Exit codes

| Code | Meaning | Emitted by |
|---|---|---|
| `0` | PASS | all subcommands |
| `2` | check FAILED (details in JSON on stdout) | precheck, lyrics-check, playlist-route, novelty-check |
| `3` | invalid input / missing file | all |
| `4` | postcheck FAILED → quarantine | postcheck; batch runner + server map this to job `quarantined` |
| `75` | another runner holds the generation flock | batch runner (not the guard itself) |
| `78` | ungated generate refused (`AUTOMATO_GATED` unset) | `suno-lib.sh` / `suno-safe.sh` |

All subcommands print a JSON report on stdout — machine-readable for agents:

```bash
python3 scripts/suno_prompt_guard.py precheck --text "$STYLE" | jq .
```

## Wiring map (who calls what)

- **Batch runner** (`scripts/suno-batch-runner.py`): all 4 pre-gates → generate →
  postcheck → novelty-history append → playlist sync. Holds the flock for the whole step.
- **Server engine** (`server/automato/engine.py: guard_gate / execute_job`): identical
  sequence for UI/REST/MCP jobs; guard preview in the dashboard uses the same calls.
- **Ungated side entrances are closed:** `suno-lib.sh generate` / `suno-safe.sh generate`
  exit `78` unless the caller passed the gate (`AUTOMATO_GATED=1`) or explicitly forces
  `--force-ungated` (loud warning).
