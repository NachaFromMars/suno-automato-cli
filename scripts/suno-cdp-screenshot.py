#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.request, time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
OUT=Path('suno-library/_diagnostics'); OUT.mkdir(parents=True, exist_ok=True)

def main():
    ts=datetime.now().strftime('%Y%m%d-%H%M%S')
    png=OUT/f'suno-cdp-real-{ts}.png'; txt=OUT/f'suno-cdp-real-{ts}.txt'
    with sync_playwright() as p:
        browser=p.chromium.connect_over_cdp('http://127.0.0.1:9233')
        ctx=browser.contexts[0] if browser.contexts else browser.new_context()
        page=ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto('https://suno.com/create', wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(7000)
        page.screenshot(path=str(png), full_page=False)
        try: body=page.locator('body').inner_text(timeout=5000)
        except Exception as e: body=f'<body error {e}>'
        txt.write_text(f'url={page.url}\n\n{body[:5000]}\n', encoding='utf-8')
        print(json.dumps({'ok':True,'screenshot':str(png),'text':str(txt),'url':page.url,'body':body[:500]},ensure_ascii=False))
        browser.close()
if __name__=='__main__': main()
