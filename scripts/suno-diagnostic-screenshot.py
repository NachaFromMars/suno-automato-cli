#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'suno-library' / '_diagnostics'
PROFILE = Path('/root/.openclaw/workspace/suno-forever-profile')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--url', default='https://suno.com/create')
    ap.add_argument('--reason', default='captcha_or_login_failure')
    args=ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ts=datetime.now().strftime('%Y%m%d-%H%M%S')
    png=OUT/f'suno-fail-{ts}.png'
    txt=OUT/f'suno-fail-{ts}.txt'
    with sync_playwright() as p:
        ctx=p.chromium.launch_persistent_context(
            str(PROFILE), headless=True,
            args=['--no-sandbox','--disable-dev-shm-usage','--disable-blink-features=AutomationControlled'],
            viewport={'width':1365,'height':900}
        )
        page=ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(8000)
            page.screenshot(path=str(png), full_page=False)
            body=''
            try: body=page.locator('body').inner_text(timeout=5000)
            except Exception as e: body=f'<body text error: {e}>'
            txt.write_text(f'url={page.url}\nreason={args.reason}\n\n{body[:5000]}\n', encoding='utf-8')
            print(json.dumps({'ok':True,'screenshot':str(png),'text':str(txt),'url':page.url},ensure_ascii=False))
        finally:
            ctx.close()
if __name__=='__main__': main()
