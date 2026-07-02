#!/usr/bin/env python3
from __future__ import annotations
import json, re, itertools, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'suno-library'

def words(s): return set(w.lower() for w in re.findall(r'[A-Za-zÀ-ỹĐđ]{3,}', s))
def jacc(a,b):
    A=words(a); B=words(b)
    return len(A&B)/max(1,len(A|B))

def main():
    metas=[]
    for p in LIB.glob('*/*/metadata.json'):
        try:
            m=json.loads(p.read_text())
            text=' '.join(str(x.get('prompt','')) for x in m.get('last_generate_payload',{}).get('data',[]) if isinstance(x,dict))
            text += ' ' + m.get('prompt','') + ' ' + m.get('title','')
            metas.append((p,m,text))
        except Exception: pass
    dup=[]
    for (p1,m1,t1),(p2,m2,t2) in itertools.combinations(metas,2):
        sim=jacc(t1,t2)
        if sim>0.42: dup.append({'a':m1.get('title'),'b':m2.get('title'),'similarity':round(sim,3)})
    scores=[]
    for p,m,t in metas:
        scores.append({'title':m.get('title'),'genre':m.get('genre'),'style':(m.get('last_audit') or {}).get('score'),'lyric':(m.get('last_lyric_audit') or {}).get('score'),'audits':len(m.get('audits',[])),'lyric_audits':len(m.get('lyric_audits',[]))})
    print(json.dumps({'projects':len(metas),'scores':scores,'possible_repetition':dup[:50]},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
