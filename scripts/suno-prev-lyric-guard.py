#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'suno-library'
def toks(s): return set(re.findall(r"[\wÀ-ỹ]+", s.lower()))
def sim(a,b):
    A,B=toks(a),toks(b)
    return len(A&B)/max(1,len(A|B)) if A and B else 0.0
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--genre',required=True); ap.add_argument('--lyrics-file',required=True); ap.add_argument('--threshold',type=float,default=0.22)
    a=ap.parse_args(); cur=Path(a.lyrics_file).read_text(encoding='utf-8')
    files=sorted((LIB/'_batch-lyrics').glob(f'{a.genre}_*.txt'), key=lambda x:x.stat().st_mtime, reverse=True)
    prev=''; prev_name=''
    for f in files:
        if f.resolve()==Path(a.lyrics_file).resolve(): continue
        txt=f.read_text(encoding='utf-8').strip()
        if txt: prev=txt; prev_name=f.name; break
    score=sim(cur,prev)
    ok=score<a.threshold
    print({'ok':ok,'similarity':round(score,3),'prev':prev_name,'threshold':a.threshold})
    return 0 if ok else 3
if __name__=='__main__': raise SystemExit(main())
