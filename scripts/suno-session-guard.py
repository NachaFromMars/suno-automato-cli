#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
PROFILE=Path.home()/'.local/share/suno-cli/chrome-profile'
DIAG=Path('suno-library/_diagnostics'); DIAG.mkdir(parents=True, exist_ok=True)

def check(profile=PROFILE, attempts=2):
    # Always refresh JWT + inject complete cookie set first.
    subprocess.run(['./scripts/suno-safe.sh','refresh'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['./scripts/suno-cookie-inject.py','--solver-profile','--no-verify'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    last={}
    with sync_playwright() as p:
        for i in range(attempts):
            ctx=p.chromium.launch_persistent_context(str(profile), headless=True, args=['--no-sandbox','--disable-dev-shm-usage','--disable-blink-features=AutomationControlled'], viewport={'width':1365,'height':900})
            page=ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto('https://suno.com/create', wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(7000)
            body=''
            try: body=page.locator('body').inner_text(timeout=5000)
            except Exception as e: body=f'<body-error {e}>'
            logged_out=('Log in' in body[:1500] or 'Join Suno for free' in body[:1500])
            checkpoint=('Failed to verify your browser' in body[:1500] or 'Vercel Security Checkpoint' in body[:1500])
            last={'url':page.url,'logged_out':logged_out,'checkpoint':checkpoint,'body':body[:600]}
            if not checkpoint:
                # Suno landing may show a Log in CTA even while API auth is valid; captcha only hard-blocks on checkpoint.
                ctx.close(); return {'ok':True, 'warning_logged_out_cta': logged_out, **last}
            # save diagnostic
            png=DIAG/f'suno-session-guard-fail-{i}.png'
            txt=DIAG/f'suno-session-guard-fail-{i}.txt'
            page.screenshot(path=str(png), full_page=False)
            txt.write_text(f'url={page.url}\nlogged_out={logged_out}\ncheckpoint={checkpoint}\n\n{body[:5000]}',encoding='utf-8')
            ctx.close()
            subprocess.run(['./scripts/suno-cookie-inject.py','--solver-profile','--no-verify'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {'ok':False, **last}

def main():
    r=check()
    print(json.dumps(r,ensure_ascii=False,indent=2))
    sys.exit(0 if r.get('ok') else 2)
if __name__=='__main__': main()
