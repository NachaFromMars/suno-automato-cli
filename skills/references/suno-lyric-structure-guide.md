# Suno Lyric Structure & Craft Guide

Authoritative reference for writing high-quality, human-touching lyrics for Suno.
Every generated lyric MUST pass `scripts/suno-structure-guard.py` before spending Suno credits.

## 1. Hard rules (non-negotiable)

1. **Rich `[section]` tags** — every song uses bracketed section tags in English, one per line, e.g. `[Intro]`, `[Verse 1]`, `[Chorus]`. Suno reads these to shape arrangement.
2. **Clean output** — the lyric file must NOT contain ```` ``` ```` code fences, a `"style"` field, a raw JSON object, or `{ }` wrappers. Only lyrics + section tags.
3. **Minimum structure** — at least 5 valid section tags, must include an Intro and a Chorus/Hook. Outro strongly recommended.
4. **Vietnamese body** — lyric lines in Vietnamese; only the bracketed section labels are English.
5. **No template repetition** — never reuse a fixed body of lines across songs. Each song is written fresh.
6. **Musical direction inside brackets** — enrich tags with instruments/energy, e.g. `[Chorus - big hook, doubled vocal, full drums]`.

## 2. Recommended section palette

Core: `[Intro]` `[Verse 1]` `[Pre-Chorus]` `[Chorus]` `[Verse 2]` `[Bridge]` `[Final Chorus]` `[Outro]`

Optional/advanced (use to shape energy):
`[Post-Chorus]` `[Hook]` `[Refrain]` `[Breakdown]` `[Build]` `[Drop]` `[Interlude]`
`[Spoken-Sung Dialogue]` `[Ad-lib]` `[Vamp]` `[Chant]` `[Mantra]` `[Call]` `[Response]` `[Coda]` `[Tag]`

Genre-specific:
- Cải lương/vọng cổ: `[Spoken-Sung Dialogue - nam/nữ]`, `[Vọng Cổ Lift]`, song loan/đàn kìm/đàn tranh in tag.
- Rap: `[Verse - double-time]`, `[Pre-Chorus - melodic lift]`, `[Hook - sung mantra]`.
- Cinematic/epic: `[Bridge - Cao trào]`, `[Final Chorus - choir + brass]`, taiko/strings in tag.
- Instrumental: `[Instrumental Intro]`, `[Instrumental Section A/B]`, no vocal lines.

## 3. Structure templates (rotate per song)

- **Classic pop**: Intro → Verse 1 → Pre-Chorus → Chorus → Verse 2 → Pre-Chorus → Chorus → Bridge → Final Chorus → Outro
- **Cold-hook**: Chorus (cold open) → Verse 1 → Chorus → Verse 2 → Bridge → Final Chorus → Outro
- **Cinematic build**: Intro → Verse 1 → Pre-Chorus → Chorus → Verse 2 → Bridge (Cao trào) → Final Chorus → Outro
- **Rap**: Intro → Verse 1 → Pre-Chorus → Hook → Verse 2 → Bridge → Hook → Outro
- **Cải lương**: Intro (nhạc cụ) → Verse 1 (vọng cổ) → Spoken-Sung Dialogue → Pre-Chorus → Chorus → Verse 2 → Bridge → Final Chorus
- **Post-chorus earworm**: Intro → Verse → Pre → Chorus → Post-Chorus → Verse 2 → Chorus → Post-Chorus → Bridge → Final Chorus + Post-Chorus

## 4. Hook / craft tips (make it touch the listener)

- **Title frame**: title appears in the first and last line of the chorus, meaning shifts by the end.
- **Rule of three, twist the third**: repeat hook twice, change the third for impact.
- **Show, don't tell**: concrete scene first (an object, a place, a gesture); let emotion be implied.
- **Object writing**: build imagery from sight, sound, touch, smell, movement.
- **Contrast phrasing**: long cinematic verse lines, short punchy chorus lines.
- **Prosody**: natural Vietnamese spoken stress must land on strong beats.
- **Metaphor collision**: fuse two unrelated concrete domains into one central image.
- **Bridge reversal**: bridge contradicts the chorus, final chorus absorbs the new truth.
- **Negative space**: leave one short line alone before the chorus for weight.
- **Slant rhyme**: prefer near-rhymes/vowel echoes over nursery-perfect rhyme.
- **One central image per song**: do not dilute; recolor it across sections.

## 5. Enforcement pipeline

1. LLM writes lyrics from seed (genre, concept, vocalist, hook shape, rhyme texture, craft technique, chosen structure template).
2. Parser unwraps any ```` ``` ```` fence and JSON wrapper, extracts the `lyrics` field only.
3. `suno-structure-guard.py --fix` cleans residual pollution and validates section tags.
4. `suno-prev-lyric-guard.py` compares against the previous song of the same genre.
5. Only a clean, well-structured lyric is sent to `suno generate`.
