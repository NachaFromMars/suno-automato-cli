#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'suno-library'
STOP=set('và của trong một những cho người không này kia với trên dưới giữa bài hát ta tôi anh em là có còn như đã'.split())
def toks(s):
    return set(w.lower() for w in re.findall(r'[A-Za-zÀ-ỹĐđ]{3,}', s) if w.lower() not in STOP)
def sim(a,b):
    A=toks(a); B=toks(b)
    return len(A&B)/max(1,len(A|B))
def recent(genre, limit=12):
    arr=[]
    for p in sorted((LIB/genre).glob('*/metadata.json'), key=lambda x:x.stat().st_mtime, reverse=True):
        try:
            m=json.loads(p.read_text())
            arr.append({'title':m.get('title',''), 'style':m.get('style_prompt','') or ', '.join(m.get('tags',[])), 'prompt':m.get('prompt',''), 'path':str(p)})
            if len(arr)>=limit: break
        except Exception: pass
    return arr
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--genre',required=True); ap.add_argument('--title',required=True); ap.add_argument('--style',required=True); ap.add_argument('--lyrics-file',required=True); ap.add_argument('--threshold',type=float,default=0.34); args=ap.parse_args()
    lyrics=Path(args.lyrics_file).read_text(encoding='utf-8') if Path(args.lyrics_file).exists() else ''
    cand=args.title+'\n'+args.style+'\n'+lyrics
    hits=[]
    for r in recent(args.genre):
        s=sim(cand, r['title']+'\n'+r['style']+'\n'+r.get('prompt',''))
        if s>=args.threshold: hits.append({'similarity':round(s,3), **r})
    out={'ok':not hits,'genre':args.genre,'title':args.title,'threshold':args.threshold,'hits':hits[:5]}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    sys.exit(0 if out['ok'] else 2)
if __name__=='__main__': main()
