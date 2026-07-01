#!/usr/bin/env python3
"""Suno style-prompt quality guard.
Rejects thin/generic style prompts. A good style prompt names instruments,
arrangement movement, tempo/energy, mood, and production. Exit 0 pass, 3 fail.
"""
from __future__ import annotations
import argparse, json, re, sys

INSTRUMENT_WORDS = ["đàn","guitar","piano","strings","cello","violin","brass","trumpet","kèn",
    "taiko","trống","drums","bass","synth","choir","flute","sáo","organ","rhodes","accordion",
    "harp","percussion","song loan","đàn kìm","đàn tranh","đàn bầu","bells","pad","808","hi-hat","snare"]
ARRANGEMENT_WORDS = ["intro","verse","chorus","bridge","build","drop","outro","climax","cao trào",
    "arrangement","layer","enters","rise","fade","lift","stripped","full","half-time","counter"]
MOOD_WORDS = ["epic","cinematic","emotional","reverent","dark","warm","tender","haunting","triumphant",
    "melancholy","hào hùng","hùng tráng","xúc động","tôn kính","u buồn","joyful","nostalgic","intimate","sầu","bi tráng"]
TEMPO_WORDS = ["bpm","tempo","slow","fast","mid","rubato","groove","pulse","nhịp"]
HOOK_WORDS = ["hook","earworm","catchy","chant","refrain","topline","riff","motif","vocal hook","instrumental hook","post-chorus","singalong","memorable"]

def score(style: str):
    s = style.lower()
    def hits(words): return sum(1 for w in words if w in s)
    inst = hits(INSTRUMENT_WORDS)
    arr = hits(ARRANGEMENT_WORDS)
    mood = hits(MOOD_WORDS)
    tempo = hits(TEMPO_WORDS)
    hook = hits(HOOK_WORDS)
    length_ok = len(style) >= 120
    ok = length_ok and inst >= 3 and arr >= 2 and mood >= 1 and tempo >= 1 and hook >= 1
    return {
        "ok": ok, "length": len(style), "length_ok": length_ok,
        "instrument_hits": inst, "arrangement_hits": arr,
        "mood_hits": mood, "tempo_hits": tempo, "hook_hits": hook,
    }

def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--style")
    g.add_argument("--style-file")
    a = ap.parse_args()
    style = a.style if a.style is not None else open(a.style_file, encoding="utf-8").read()
    r = score(style.strip())
    print(json.dumps(r, ensure_ascii=False))
    return 0 if r["ok"] else 3

if __name__ == "__main__":
    raise SystemExit(main())
