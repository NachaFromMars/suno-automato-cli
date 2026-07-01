#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

AUTH = Path.home() / '.config/suno-cli/auth.json'
DEFAULT_PROFILE = Path('/root/.openclaw/workspace/suno-forever-profile')
SOLVER_PROFILE = Path.home() / '.local/share/suno-cli/chrome-profile'

def parse_cookie_header(header: str):
    for part in header.split(';'):
        if '=' in part:
            k, v = part.strip().split('=', 1)
            if k and v:
                yield k, v

def build_cookies(auth: dict):
    """Build a durable Suno web-cookie set from persisted auth.json.

    Important: __client alone is not enough for the web app. Include __session
    and set auth/app domains so new tabs/profiles do not appear logged out.
    """
    cookies = []
    clerk = auth.get('clerk_client_cookie')
    if clerk:
        for domain in ['.suno.com', 'suno.com', 'auth.suno.com']:
            cookies.append({'name':'__client','value':clerk,'domain':domain,'path':'/','secure':True,'httpOnly':False,'sameSite':'Lax'})
    if auth.get('session_id'):
        for domain in ['.suno.com', 'suno.com', 'auth.suno.com']:
            cookies.append({'name':'__session','value':auth['session_id'],'domain':domain,'path':'/','secure':True,'httpOnly':True,'sameSite':'Lax'})
    if auth.get('cookie'):
        for name, value in parse_cookie_header(auth['cookie']):
            domains = ['.suno.com', 'suno.com']
            if name == '__client' or name == '__session' or 'clerk' in name.lower():
                domains.append('auth.suno.com')
            for domain in domains:
                cookies.append({'name':name,'value':value,'domain':domain,'path':'/','secure':True,'httpOnly':False,'sameSite':'Lax'})
    if auth.get('device_id'):
        for name in ['ajs_anonymous_id', 'suno_device_id']:
            cookies.append({'name':name,'value':auth['device_id'],'domain':'.suno.com','path':'/','secure':False,'httpOnly':False,'sameSite':'Lax'})
            cookies.append({'name':name,'value':auth['device_id'],'domain':'suno.com','path':'/','secure':False,'httpOnly':False,'sameSite':'Lax'})
    seen=set(); out=[]
    for c in cookies:
        key=(c['name'],c['domain'])
        if key not in seen:
            seen.add(key); out.append(c)
    return out

def inject(profile: Path, verify: bool = True):
    auth = json.loads(AUTH.read_text())
    cookies = build_cookies(auth)
    profile.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(profile), headless=True, args=['--no-sandbox','--disable-dev-shm-usage'], viewport={'width':1365,'height':900})
        ctx.add_cookies(cookies)
        result = {'profile': str(profile), 'cookies_set': len(cookies)}
        if verify:
            page = ctx.new_page()
            page.goto('https://suno.com/create', wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(5000)
            body = page.locator('body').inner_text(timeout=5000)
            result['url'] = page.url
            result['logged_in'] = ('Log in' not in body[:1000] and 'Join Suno for free' not in body[:1000])
            result['body_excerpt'] = body[:500]
        ctx.close()
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--profile', default=str(DEFAULT_PROFILE))
    ap.add_argument('--solver-profile', action='store_true', help='Inject into suno-cli captcha solver profile')
    ap.add_argument('--no-verify', action='store_true')
    args=ap.parse_args()
    targets=[Path(args.profile)]
    if args.solver_profile:
        targets.append(SOLVER_PROFILE)
    results=[inject(t, verify=not args.no_verify) for t in targets]
    print(json.dumps({'ok':True,'results':results},ensure_ascii=False,indent=2))
if __name__ == '__main__': main()
