#!/usr/bin/env python3
"""Suno lyric structure guard.
Ensures a lyric file is clean (no JSON/code-fence pollution) and has a rich,
Suno-friendly [section] structure before we ever spend Suno credits.
Exit 0 = pass, 3 = fail. Prints a JSON report.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

VALID_SECTION_WORDS = [
    "intro","verse","pre-chorus","prechorus","chorus","post-chorus","postchorus",
    "hook","bridge","breakdown","drop","build","refrain","interlude","outro",
    "spoken","spoken-sung","dialogue","ad-lib","adlib","vamp","instrumental",
    "final chorus","coda","tag","chant","mantra","call","response",
]

def clean_text(raw: str) -> str:
    t = raw.strip()
    # strip ```json ... ``` or ``` ... ``` fences
    fence = re.match(r"^```[a-zA-Z]*\s*(.*?)\s*```$", t, re.S)
    if fence:
        t = fence.group(1).strip()
    # if it's a JSON object with a lyrics field, extract it
    if t.startswith("{"):
        try:
            obj = json.loads(t)
            if isinstance(obj, dict) and obj.get("lyrics"):
                t = str(obj["lyrics"]).strip()
        except Exception:
            m = re.search(r'"lyrics"\s*:\s*"(.*?)"\s*[,}]', t, re.S)
            if m:
                t = m.group(1).encode().decode("unicode_escape")
    return t.strip()

def section_tags(t: str):
    return re.findall(r"^\[([^\]]+)\]", t, re.M)

def analyze(raw: str):
    cleaned = clean_text(raw)
    tags = section_tags(cleaned)
    valid = [tag for tag in tags if any(w in tag.lower() for w in VALID_SECTION_WORDS)]
    has_chorus = any("chorus" in tag.lower() or "hook" in tag.lower() for tag in tags)
    has_intro = any("intro" in tag.lower() for tag in tags)
    has_outro = any("outro" in tag.lower() or "coda" in tag.lower() for tag in tags)
    has_hook = any("hook" in tag.lower() for tag in tags) or any("chorus" in tag.lower() for tag in tags)
    pollution = bool(re.search(r"```|\"style\"|\"lyrics\"|^\s*\{", cleaned)) or cleaned.strip().startswith("{")
    ok = (len(valid) >= 5) and has_chorus and has_intro and has_hook and not pollution
    return {
        "ok": ok,
        "cleaned": cleaned,
        "section_count": len(tags),
        "valid_section_count": len(valid),
        "has_intro": has_intro,
        "has_chorus": has_chorus,
        "has_outro": has_outro,
        "has_hook": has_hook,
        "pollution": pollution,
        "tags": tags,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lyrics-file", required=True)
    ap.add_argument("--fix", action="store_true", help="rewrite the file with cleaned lyrics if only pollution was the issue")
    a = ap.parse_args()
    p = Path(a.lyrics_file)
    raw = p.read_text(encoding="utf-8")
    r = analyze(raw)
    if a.fix and r["cleaned"] and r["cleaned"] != raw.strip():
        p.write_text(r["cleaned"] + "\n", encoding="utf-8")
        r = analyze(p.read_text(encoding="utf-8"))
        r["fixed"] = True
    report = {k: v for k, v in r.items() if k != "cleaned"}
    print(json.dumps(report, ensure_ascii=False))
    return 0 if r["ok"] else 3

if __name__ == "__main__":
    raise SystemExit(main())
