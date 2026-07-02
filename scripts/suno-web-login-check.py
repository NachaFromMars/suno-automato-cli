#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
PROFILE=Path.home()/'.local/share/suno-cli/chrome-profile'
AUTH=Path.home()/'.config/suno-cli/auth.json'

def parse_cookie_header(header):
    for part in header.split(';'):
        if '=' in part:
            k,v=part.strip().split('=',1)
            if k and v: yield k,v

def inject(ctx):
    a=json.loads(AUTH.read_text())
    cookies=[]
    # More complete cookie set than earlier: auth + app domains, including __session from header.
    if a.get('clerk_client_cookie'):
        for d in ['auth.suno.com','.suno.com','suno.com']:
            cookies.append({'name':'__client','value':a['clerk_client_cookie'],'domain':d,'path':'/','secure':True,'httpOnly':False,'sameSite':'Lax'})
    if a.get('cookie'):
        for name,value in parse_cookie_header(a['cookie']):
            for d in ['.suno.com','suno.com','auth.suno.com']:
                cookies.append({'name':name,'value':value,'domain':d,'path':'/','secure':True,'httpOnly':False,'sameSite':'Lax'})
    if a.get('session_id'):
        for d in ['.suno.com','suno.com','auth.suno.com']:
            cookies.append({'name':'__session','value':a['session_id'],'domain':d,'path':'/','secure':True,'httpOnly':True,'sameSite':'Lax'})
    if a.get('device_id'):
        cookies.append({'name':'ajs_anonymous_id','value':a['device_id'],'domain':'.suno.com','path':'/','secure':False,'httpOnly':False,'sameSite':'Lax'})
        cookies.append({'name':'suno_device_id','value':a['device_id'],'domain':'.suno.com','path':'/','secure':True,'httpOnly':False,'sameSite':'Lax'})
    seen=set(); out=[]
    for c in cookies:
        key=(c['name'],c['domain'])
        if key not in seen:
            seen.add(key); out.append(c)
    ctx.add_cookies(out)
    return len(out)

def main():
    with sync_playwright() as p:
        ctx=p.chromium.launch_persistent_context(str(PROFILE), headless=True, args=['--no-sandbox','--disable-dev-shm-usage','--disable-blink-features=AutomationControlled'], viewport={'width':1365,'height':900})
        n=inject(ctx)
        page=ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto('https://suno.com/create', wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(8000)
        body=page.locator('body').inner_text(timeout=5000)
        # Also inspect cookies visible after redirects.
        names=sorted({c['name']+'@'+c['domain'] for c in ctx.cookies() if 'suno' in c.get('domain','')})
        print(json.dumps({'url':page.url,'logged_out':('Log in' in body[:1500] or 'Join Suno for free' in body[:1500]),'body':body[:1000],'cookies_injected':n,'cookie_names':names[:80]},ensure_ascii=False,indent=2))
        ctx.close()
if __name__=='__main__': main()
