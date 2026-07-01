# Suno V5.5 Maestro Prompting

Goal: every generation should sound produced, not merely tagged.

## Core finding

Use Custom Mode and treat inputs as two separate producer briefs:

1. **Style of Music** = sonic identity and production direction.
2. **Lyrics** = lyric content plus arrangement/performance cues.

Do not use short generic tags like `Vietnamese rap, deep bass`. Suno v5.5 needs a compact but information-dense producer prompt.

## Style prompt schema

Keep the style field focused, ordered, and non-contradictory:

```text
[quality + primary subgenre], [tempo + groove], [vocal identity + delivery], [beat/drums + bass], [instrument hooks + texture], [production/mix], [emotion/energy arc], [arrangement cue]
```

Recommended fields:

- **Quality anchor:** hyper-realistic, commercial master, radio-ready, cinematic mix.
- **Primary + subgenre:** do not say only `rap`; say `Vietnamese conscious rap over cinematic boom-bap/trap hybrid`.
- **Tempo/groove:** BPM or feel, half-time, swing, four-on-the-floor, syncopated, shuffle.
- **Vocal identity:** male/female, smoky/raspy/breathy/chest voice/falsetto, rap verses + sung hook, call-and-response, layered backing vocals.
- **Flow:** triplet flow, staccato, syncopated internal rhymes, spoken-word intro, melodic hook, double-time bridge.
- **Beat/drums:** 808 glide bass, dusty boom-bap drums, live kit, gated snare, hi-hat rolls, taiko, brushed drums.
- **Harmony/key/timbre:** minor key, modal, jazz chords, suspended chords, pentatonic motif.
- **Instrument hooks:** bamboo flute riff, đàn bầu glissando, distorted guitar riff, Rhodes, glassy arps, temple bell.
- **Production/mix:** sidechain compression, tape saturation, wide stereo chorus, dry intimate verse, huge reverb hook, crisp transient drums.
- **Emotion arc:** restrained verse → explosive chorus → stripped bridge → final lift.
- **Negative/exclude:** avoid the biggest failure modes only, 2-4 items max.

## Style length rule

Suno style fields have limits. Prefer one precise sentence or comma-separated clauses under ~900 chars; if a command has a smaller field cap, compress to the highest-value descriptors.

## Lyrics schema

Use arrangement tags and performance cues directly in the lyrics field:

```text
[Intro - spoken, dry vocal, sparse texture]
...

[Verse 1 - low energy, tight rhythmic rap, internal rhyme]
...

[Pre-Chorus - melodic lift, harmony enters]
...

[Chorus - big hook, doubled vocal, memorable repeated phrase]
...

[Verse 2 - denser flow, drums add hi-hats]
...

[Bridge - stripped, half-time, emotional turn]
...

[Final Chorus - larger, ad-libs, stacked harmonies]
...

[Outro - motif returns, clean ending]
```

## Negative prompt defaults

Use `--exclude` when the CLI supports it. Keep it short:

- generic pop, stock loop, karaoke, muddy mix, offbeat drums
- for rap: mumble rap, monotone vocal, weak hook
- for meditation: EDM drop, harsh drums, aggressive vocal
- for rock: pop punk cliché, thin guitars, weak drums

## Sliders

For creative but stable results:

- `--weirdness 55-65` for unique but not broken generations.
- `--style-influence 75-90` when the style prompt is detailed and intentional.
- Lower weirdness for ballad/pop if vocal clarity matters.

## Post-generation audit

Every generated project should be audited and recorded in metadata:

- **Style richness:** Does it contain genre/subgenre + tempo/groove + instrument hooks + production?
- **Vocal/flow clarity:** Are voice and performance instructions explicit?
- **Beat/bass specificity:** Are drums, bass, groove described?
- **Arrangement arc:** Are sections and energy changes clear?
- **Hook strength:** Is there a repeated memorable chorus phrase?
- **Uniqueness:** Does it avoid generic style words and repeated patterns?
- **Technical controls:** Weirdness/style influence/exclude set?

If score < 8/10, upgrade the next prompt by adding missing layers and avoiding the failure mode.

## v0.5.0 Maestro upgrade: style chain template

Every new batch now goes through `scripts/suno-seed-engine.py` before generation. The style prompt must not be a flat comma list. It is a chained producer brief:

```text
Hyper-realistic commercial Suno v5.5 master;
[GENRE] genre DNA: BPM + groove;
vocal/performance chain: voice archetype + delivery + hook behavior;
beat/bass/drum chain: drum source + bass behavior + transient/mix notes;
signature concept motif: one fresh image seed;
hook design: one explicit hook shape;
arrangement map: intro → verse → lift → chorus/drop → bridge → final lift;
mix target: transient clarity + low-end separation + stereo width + no pop-washing
```

Rules:
- First tokens carry the strongest direction: start with primary genre + subgenre DNA.
- Each song receives a different image seed and hook shape to prevent repeated lyrics.
- Negative prompt always includes anti-repetition constraints.
- Weirdness/style influence are explicit, not defaulted silently.
- If audit score drops below 8, the evolution memory records the missing dimension.
