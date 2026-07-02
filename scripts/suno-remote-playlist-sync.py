#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, requests, re
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'suno-library'
AUTH=Path.home()/'.config/suno-cli/auth.json'
BASE='https://studio-api-prod.suno.com'

def load_auth():
    a=json.loads(AUTH.read_text())
    return {
        'authorization':'Bearer '+a['jwt'],
        'origin':'https://suno.com', 'referer':'https://suno.com/',
        'user-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'device-id':a.get('device_id','00000000-0000-0000-0000-000000000000'),
        'browser-token':'web', 'content-type':'application/json'
    }

def slug(s): return re.sub('-+','-', ''.join(ch if ch.isalnum() else '-' for ch in s)).strip('-')
def get_json(method,path,h,**kw):
    r=requests.request(method, BASE+path, headers=h, timeout=40, **kw)
    if not r.ok: raise RuntimeError(f'{method} {path} {r.status_code}: {r.text[:500]}')
    return r.json() if r.text else {}

def list_playlists(h):
    out=[]; page=0
    while True:
        data=get_json('GET',f'/api/playlist/me/?page={page}',h)
        pls=data.get('playlists') or []
        out.extend(pls)
        if len(pls)<12 or len(out)>=data.get('num_total_results',len(out)): break
        page+=1
    return out

def create_playlist(h,name):
    return get_json('POST','/api/playlist/create/',h,json={'name':name})

def add_clips(h,pid,clip_ids):
    if not clip_ids: return {'skipped':True}
    body={'playlist_id':pid,'update_type':'add','metadata':{'clip_ids':clip_ids},'recommendation_metadata':{}}
    r=requests.post(BASE+'/api/playlist/update_clips/',headers=h,json=body,timeout=60)
    if not r.ok:
        # fallback v2 endpoint discovered in JS chunks
        r=requests.post(BASE+f'/api/playlist/v2/{pid}/tracks/add',headers=h,json={'clip_ids':clip_ids},timeout=60)
    if not r.ok: raise RuntimeError(f'add clips {pid} {r.status_code}: {r.text[:500]}')
    return r.json() if r.text else {'ok':True}

def local_albums():
    albums=[]
    for p in sorted((LIB/'_albums').glob('*/album.json')):
        m=json.loads(p.read_text())
        tracks=[t for t in m.get('tracks',[]) if t.get('suno_id')]
        albums.append((p,m,tracks))
    return albums

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--limit',type=int,default=0)
    args=ap.parse_args()
    h=load_auth()
    existing=list_playlists(h)
    by_name={p.get('name'):p for p in existing}
    report=[]
    albums=local_albums()
    if args.limit: albums=albums[:args.limit]
    for path,album,tracks in albums:
        name=album['name']
        remote=by_name.get(name)
        created=False
        if not remote:
            if args.dry_run:
                remote={'id':'DRY-RUN','name':name}; created=True
            else:
                remote=create_playlist(h,name); by_name[name]=remote; created=True
        pid=remote['id']
        # fetch detail to avoid duplicate add where possible
        existing_ids=set()
        if not args.dry_run and pid!='DRY-RUN':
            try:
                detail=get_json('GET',f'/api/playlist/{pid}/?page=0',h)
                for pc in detail.get('playlist_clips',[]):
                    cid=(pc.get('clip') or {}).get('id')
                    if cid: existing_ids.add(cid)
            except Exception: pass
        clip_ids=[]
        for t in tracks:
            cid=t.get('suno_id')
            if cid and cid not in existing_ids and cid not in clip_ids: clip_ids.append(cid)
        if args.dry_run:
            add_result={'dry_run_add':len(clip_ids)}
        else:
            add_result=add_clips(h,pid,clip_ids) if clip_ids else {'skipped':'no_new_clips'}
            album['remote_album_sync']='synced_suno_playlist'
            album['remote_playlist_id']=pid
            album['remote_synced_at']=datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
            path.write_text(json.dumps(album,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        report.append({'name':name,'playlist_id':pid,'created':created,'local_tracks':len(tracks),'added':len(clip_ids),'result':add_result})
    print(json.dumps({'ok':True,'albums':report},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
