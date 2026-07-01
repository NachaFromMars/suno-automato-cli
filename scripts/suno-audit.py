#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

CHECKS = {
    'primary_subgenre': [r'rap|rock|pop|ballad|edm|lo-?fi|ambient|cinematic|folk|jazz|house|trap|boom-bap|synth'],
    'tempo_groove': [r'\b\d{2,3}\s?BPM\b', r'half-time|double-time|four-on-the-floor|swing|shuffle|syncopated|groove'],
    'vocal_identity': [r'vocal|voice|falsetto|raspy|breathy|chest voice|spoken|rapped|sung|harmony|ad-lib'],
    'flow_delivery': [r'flow|staccato|triplet|internal rhyme|melodic hook|call-and-response|spoken-word|double-time'],
    'beat_bass_drums': [r'808|kick|snare|hi-hat|drum|bass|boom-bap|breakbeat|taiko|percussion'],
    'instrument_hook': [r'guitar|piano|Rhodes|synth|flute|bell|strings|brass|đàn|dan bau|erhu|choir|riff|motif'],
    'production_mix': [r'mix|master|reverb|compression|sidechain|stereo|tape|saturation|transient|lo-fi|glossy|gritty'],
    'emotion_arc': [r'arc|build|restrained|explosive|euphoric|melancholic|tense|intimate|lift|stripped'],
}
SECTION_TAGS = ['Intro','Verse','Pre-Chorus','Chorus','Hook','Bridge','Break','Drop','Outro','Final Chorus']

def score_text(style: str, lyrics: str, exclude: str = '', weirdness=None, style_influence=None):
    results = {}
    for name, pats in CHECKS.items():
        results[name] = any(re.search(p, style, re.I) for p in pats)
    sections = sum(1 for tag in SECTION_TAGS if re.search(r'\[' + re.escape(tag), lyrics, re.I))
    results['arrangement_sections'] = sections >= 5
    results['performance_cues'] = bool(re.search(r'\[[^\]]*(spoken|whisper|low energy|high energy|harmony|ad-lib|stripped|build|drop|doubled|dry vocal)[^\]]*\]', lyrics, re.I))
    results['exclude_styles'] = bool(exclude.strip())
    results['sliders'] = weirdness is not None and style_influence is not None
    passed = sum(results.values())
    total = len(results)
    score = round(10 * passed / total, 1)
    missing = [k for k,v in results.items() if not v]
    lessons = []
    if missing:
        lessons.append('Next prompt must add: ' + ', '.join(missing))
    if len(style) < 160:
        lessons.append('Style prompt too short; expand into producer brief.')
    if 'Chorus' not in lyrics:
        lessons.append('Add a repeated chorus/hook.')
    return {'score': score, 'passed': passed, 'total': total, 'checks': results, 'missing': missing, 'lessons': lessons}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--style', default='')
    ap.add_argument('--lyrics-file')
    ap.add_argument('--exclude', default='')
    ap.add_argument('--weirdness', type=int)
    ap.add_argument('--style-influence', type=int)
    args=ap.parse_args()
    project=Path(args.project)
    meta_path=project/'metadata.json'
    meta=json.loads(meta_path.read_text(encoding='utf-8')) if meta_path.exists() else {}
    lyrics=Path(args.lyrics_file).read_text(encoding='utf-8') if args.lyrics_file else meta.get('lyrics','')
    style=args.style or meta.get('style_prompt') or ', '.join(meta.get('tags', []))
    audit=score_text(style, lyrics, args.exclude, args.weirdness, args.style_influence)
    audit['at']=datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
    audit['style_prompt']=style
    audit['exclude']=args.exclude
    audit['weirdness']=args.weirdness
    audit['style_influence']=args.style_influence
    meta.setdefault('audits', []).append(audit)
    meta['last_audit']=audit
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(audit, ensure_ascii=False, indent=2))
if __name__=='__main__': main()
