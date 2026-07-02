#!/usr/bin/env python3
from __future__ import annotations
import json, csv
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'suno-library'
ALBUMS=LIB/'_albums'

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    projects=[]
    for meta in LIB.glob('*/*/metadata.json'):
        m=read(meta); projects.append((meta.parent,m))
    by_album={}
    for p,m in projects:
        album=m.get('album') or f"{m.get('genre','Other')} Vol.1"
        by_album.setdefault(album,[]).append((p,m))
    for album,items in by_album.items():
        genre=items[0][1].get('genre','Other')
        import re
        slug=re.sub('-+', '-', ''.join(ch if ch.isalnum() else '-' for ch in album)).strip('-')
        adir=ALBUMS/slug
        manifest=read(adir/'album.json') if (adir/'album.json').exists() else {'schema_version':'1.0','name':album,'slug':slug,'genre':genre,'created_at':datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')}
        tracks=[]
        for p,m in sorted(items,key=lambda x:x[1].get('created_at','')):
            for t in m.get('takes',[]):
                tracks.append({
                    'title':t.get('title'), 'project_title':m.get('title'), 'take_no':t.get('take_no'), 'label':t.get('label'),
                    'suno_id':t.get('suno_id'), 'audio_path':t.get('audio_path'), 'status':t.get('status','draft'),
                    'cover_path':t.get('cover_path',''), 'image_url':t.get('image_url',''), 'style_score':(m.get('last_audit') or {}).get('score'), 'lyric_score':(m.get('last_lyric_audit') or {}).get('score')
                })
        manifest.update({'name':album,'slug':slug,'genre':genre,'track_count':len(tracks),'project_count':len(items),'tracks':tracks,'remote_album_sync':manifest.get('remote_album_sync','pending_cli_or_browser_sync'),'updated_at':datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')})
        write(adir/'album.json',manifest)
        # markdown playlist
        md=[f"# {album}","",f"Genre: {genre}",f"Tracks: {len(tracks)}",f"Remote Suno sync: {manifest['remote_album_sync']}","","## Tracks",""]
        for i,t in enumerate(tracks,1):
            md.append(f"{i}. {t['title']} — Suno `{t.get('suno_id')}` — style {t.get('style_score')} / lyric {t.get('lyric_score')}")
            md.append(f"   - `{t.get('audio_path')}`")
        (adir/'PLAYLIST.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
        # csv
        with (adir/'tracks.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['title','project_title','take_no','label','suno_id','audio_path','cover_path','image_url','status','style_score','lyric_score'])
            w.writeheader(); w.writerows(tracks)
    print(json.dumps({'albums':len(by_album),'tracks':sum(len(v) for v in by_album.values())},ensure_ascii=False))
if __name__=='__main__': main()
