# Suno V5.5 Lyric Maestro

Purpose: make lyrics singable, hook-driven, structurally clear, and self-improving after every generation.

## Key rules for Suno V5/V5.5 lyrics

- Use **Custom Lyrics** whenever quality matters.
- Treat the lyrics box as a **song structure + performance map**, not a poem dump.
- Use clear section tags on their own line.
- Keep total lyrics focused: about **200-350 words** for most genres, up to **500** for rap.
- Maintain similar line length inside corresponding sections; Suno aligns syllables to beats.
- Prefer **6-10 syllables per line** for sung sections; rap can be denser but must keep cadence.
- Chorus should be short: **2-4 lines**, memorable, and repeated explicitly when needed.
- Strong opening line matters: Suno gives high melodic weight to the first line of each tagged section.
- Put vocal/performance cues inside section tags, not as long prose.

## Recommended lyric skeleton

```text
[Intro - short instrumental motif, spoken ad-lib]
(optional 1-2 lines)

[Verse 1 - focused lead vocal, low-to-mid energy]
4-8 lines, similar syllable length

[Pre-Chorus - harmony enters, tension builds]
2-4 lines, lift toward hook

[Chorus - big memorable hook, doubled vocal, full drums]
2-4 lines, repeatable, title phrase appears

[Verse 2 - denser delivery, added percussion layer]
4-8 lines, mirrors Verse 1 rhythm but advances story

[Bridge - stripped arrangement, emotional turn]
2-4 lines, contrast or revelation

[Final Chorus - bigger hook, ad-libs, stacked harmonies]
repeat or slightly vary chorus

[Outro - motif returns, clean ending]
1-3 lines or instrumental cue
```

## Lyric audit rubric

Score each generated project after generation:

1. **Structure clarity**: intro/verse/pre/chorus/bridge/outro present where genre requires.
2. **Performance cues**: section tags include vocal/energy/arrangement directives.
3. **Hook strength**: chorus is 2-4 lines, title/central phrase appears, memorable repetition.
4. **Syllable/rhythm consistency**: line lengths are not wildly uneven.
5. **Singability**: avoids tongue-twister prose, overlong lines, abstract clutter.
6. **Emotional arc**: verse sets scene, pre lifts tension, chorus releases, bridge turns.
7. **Genre fit**: rap has flow/density/internal rhyme; ballad has melodic breathing room; EDM has build/drop; ambient/mantra has repetition.
8. **Vietnamese prosody**: natural word order, vowel-rich endings, not too many hard consonant clusters.
9. **No prompt leakage**: no accidental technical instructions sung as lyrics unless intentionally bracketed.
10. **Length discipline**: not too short to be trivial, not too long to rush.

## Evolution rule

If lyric audit < 8/10:

- Save missing dimensions into `metadata.json -> lyric_audits[]`.
- Append lessons into `suno-library/maestro-evolution.json`.
- Next batch must apply active lessons before generating.

Typical upgrades:

- Weak hook → shorten chorus, repeat title phrase, add vowel-rich line ending.
- Rushed vocal → reduce line length, split long lines, simplify punctuation.
- Flat emotion → add pre-chorus lift and bridge contrast.
- Generic rap → add flow cue, internal rhyme, punchline cadence, breath points.
- Weak Suno parsing → add clear blank lines and bracketed section tags.

## v0.5.0 Lyric diversity upgrade

New generations pass through `scripts/suno-seed-engine.py`, which assigns each song a unique idea seed:

- image object: e.g. `glass orchard`, `subway temple`, `ink river`
- Vietnamese sensory phrase
- thematic axis
- hook shape
- rhyme texture
- arrangement map

The lyric generator must avoid reusing the same spiritual/self-return vocabulary across songs unless the genre specifically requires it. Each new lyric should vary:

- location/scene
- metaphor family
- rhyme scheme
- hook syntax
- emotional turn
- perspective/zoom level

Audit should flag repetition via future similarity checks. Any song that repeats the same image family or chorus structure gets a lesson added to `maestro-evolution.json`.

## v0.6.0 Hard diversity gate

Before generation, `scripts/suno-diversity-guard.py` compares the candidate title + style + lyrics against recent projects in the same genre. If similarity is above threshold, the batch runner reseeds the song before spending credits.

Mandatory differences per generation:
- different central image / setting
- different hook phrase and hook shape
- different rhyme texture
- different emotional turn
- different vocalist/instrument lead where applicable
- different groove/production-chain clauses

If 8 reseeds still fail the threshold, generation stops and reports a blocker instead of producing another near-duplicate.
