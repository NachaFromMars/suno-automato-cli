#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, statistics
from datetime import datetime, timezone
from pathlib import Path

SECTION_RE = re.compile(r'^\s*\[([^\]]+)\]\s*$', re.M)
CORE = ['Intro','Verse','Chorus','Bridge','Outro']
CUES = r'spoken|whisper|vocal|harmony|ad-lib|energy|build|stripped|doubled|full drums|hook|drop|instrumental|choir|belting|soft|rap|sung|lead'
VOWELS = 'aăâeêioôơuưyAĂÂEÊIOÔƠUƯY'

def strip_tags(text):
    return re.sub(r'^\s*\[[^\]]+\]\s*$', '', text, flags=re.M).strip()

def sections(text):
    tags=[]
    for m in SECTION_RE.finditer(text):
        tags.append((m.group(1), m.start(), m.end()))
    chunks=[]
    for i,(tag,start,end) in enumerate(tags):
        nxt=tags[i+1][1] if i+1<len(tags) else len(text)
        body=text[end:nxt].strip()
        chunks.append((tag, body))
    return chunks

def word_lines(body):
    return [ln.strip() for ln in body.splitlines() if ln.strip() and not ln.strip().startswith('[')]

def approx_syllables_vi(line):
    # Vietnamese rough syllable proxy: count whitespace-separated words containing vowels.
    words=re.findall(r"[A-Za-zÀ-ỹĐđ']+", line)
    return sum(1 for w in words if any(v in w for v in VOWELS))

def audit(lyrics):
    chunks=sections(lyrics)
    all_lines=[]
    for _,body in chunks: all_lines.extend(word_lines(body))
    counts=[approx_syllables_vi(x) for x in all_lines if x]
    section_names=[t.lower() for t,_ in chunks]
    chorus_bodies=[body for tag,body in chunks if 'chorus' in tag.lower() or 'hook' in tag.lower()]
    chorus_lines=[]
    for body in chorus_bodies: chorus_lines.extend(word_lines(body))
    title_phrase_repeated=False
    if chorus_lines:
        joined=' '.join(chorus_lines).lower()
        words=re.findall(r'[A-Za-zÀ-ỹĐđ]+', joined)
        title_phrase_repeated = any(joined.count(' '.join(words[i:i+2]))>=2 for i in range(max(0,len(words)-1)))
    checks={}
    checks['structure_tags']=len(chunks)>=5 and any('verse' in x for x in section_names) and any(('chorus' in x or 'hook' in x) for x in section_names)
    checks['performance_cues']=sum(1 for tag,_ in chunks if re.search(CUES, tag, re.I))>=3
    checks['chorus_present']=bool(chorus_bodies)
    checks['chorus_concise']=bool(chorus_lines) and 2 <= len(chorus_lines) <= 6
    checks['hook_repeatability']=bool(chorus_lines) and (len(chorus_lines)<=4 or title_phrase_repeated)
    checks['line_length_consistency']=bool(counts) and (statistics.pstdev(counts) <= 4.0 if len(counts)>1 else True)
    checks['singable_line_lengths']=bool(counts) and sum(1 for c in counts if 4 <= c <= 14) / len(counts) >= 0.75
    checks['emotional_arc']=any('pre' in x for x in section_names) and any('bridge' in x for x in section_names) and any('final' in x or 'outro' in x for x in section_names)
    checks['blank_line_separation']='\n\n[' in lyrics
    checks['length_discipline']=120 <= len(re.findall(r'[A-Za-zÀ-ỹĐđ]+', strip_tags(lyrics))) <= 520
    passed=sum(checks.values()); total=len(checks); score=round(10*passed/total,1)
    missing=[k for k,v in checks.items() if not v]
    lessons=[]
    if missing: lessons.append('Next lyric must improve: '+', '.join(missing))
    if not checks['chorus_concise']: lessons.append('Make chorus/hook 2-4 strong lines; repeat title phrase explicitly.')
    if not checks['line_length_consistency']: lessons.append('Normalize syllable counts across verse lines; split long lines.')
    if not checks['performance_cues']: lessons.append('Add vocal/energy/arrangement cues inside section tags.')
    return {'score':score,'passed':passed,'total':total,'checks':checks,'missing':missing,'lessons':lessons,'line_syllables':counts[:80], 'sections':[t for t,_ in chunks]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--lyrics-file', required=True)
    args=ap.parse_args()
    project=Path(args.project); meta_path=project/'metadata.json'
    lyrics=Path(args.lyrics_file).read_text(encoding='utf-8')
    result=audit(lyrics)
    result['at']=datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
    result['lyrics_file']=str(Path(args.lyrics_file).resolve())
    meta=json.loads(meta_path.read_text(encoding='utf-8')) if meta_path.exists() else {}
    meta.setdefault('lyric_audits', []).append(result)
    meta['last_lyric_audit']=result
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__=='__main__': main()
