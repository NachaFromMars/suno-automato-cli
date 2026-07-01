#!/usr/bin/env python3
"""Write ONE Suno song (bespoke lyrics + bespoke style) for a given seed.

Guarantees:
- lyrics have rich English [Section] tags (structure guard),
- style is a bespoke, instrument/arrangement/mood-rich prompt (style guard),
- output is clean (no code fences / JSON wrappers).

Usage:
  suno-song-writer.py --genre Cinematic-MaxMax --title "..." --concept "..." \
     --genre-brief "epic trailer" [--prev-file path] --out-lyrics L.txt --out-style S.txt
Prints JSON {"title","lyrics_file","style_file","structure_ok","style_ok"}.
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import random as _rnd
HOOK_TYPES = [
    "vocal hook lặp lại bắt tai (earworm)",
    "instrumental hook / motif nhạc cụ dễ nhớ",
    "chant hook (đám đông hô theo được)",
    "post-chorus vowel tag ngắn",
    "call-and-response hook",
    "question-answer hook",
    "title-drop hook (tên bài lặp ở hook)",
    "riff-based hook (guitar/brass/strings riff)",
]
MODELS = [
    os.environ.get("SUNO_LYRIC_MODEL", "gptplus4/cx/gpt-5.5"),
    "router9/cc/claude-sonnet-4-6",
    "router9/cc/claude-haiku-4-5-20251001",
    "venice/openai-gpt-4o-mini-2024-07-18",
]

def unwrap(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```[a-zA-Z]*\s*(.*?)\s*```$", t, re.S)
    if m:
        t = m.group(1).strip()
    return t

def call_llm(prompt: str):
    for mdl in MODELS:
        try:
            proc = subprocess.run(
                ["openclaw", "infer", "model", "run", "--gateway", "--model", mdl, "--prompt", prompt, "--json"],
                cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240)
            raw = proc.stdout
            m = re.search(r"\{.*\}", raw, re.S)
            if not m:
                continue
            obj = json.loads(m.group(0))
            text = obj.get("outputs", [{}])[0].get("text", "") if "outputs" in obj else raw
            text = unwrap(str(text))
            inner = re.search(r"\{.*\}", text, re.S)
            if inner:
                try:
                    song = json.loads(inner.group(0))
                    if song.get("lyrics") and song.get("style"):
                        return song.get("title", ""), str(song["lyrics"]).strip(), str(song["style"]).strip(), mdl
                except Exception:
                    pass
        except Exception:
            continue
    return None, None, None, None

def guard_structure(path: Path):
    p = subprocess.run([str(ROOT/"scripts"/"suno-structure-guard.py"), "--lyrics-file", str(path), "--fix"],
                       text=True, stdout=subprocess.PIPE)
    try: return json.loads(p.stdout).get("ok", False)
    except Exception: return False

def guard_style(style: str):
    p = subprocess.run([str(ROOT/"scripts"/"suno-style-guard.py"), "--style", style],
                       text=True, stdout=subprocess.PIPE)
    try: return json.loads(p.stdout).get("ok", False)
    except Exception: return False

def build_prompt(genre, title, concept, genre_brief, prev, hook_type):
    return f"""Bạn là nhạc sĩ + sound designer chuyên nghiệp. Viết MỘT bài hát cho Suno, chất lượng cao, chạm cảm xúc.

Thể loại: {genre} ({genre_brief})
Tiêu đề gợi ý: {title}
Concept (câu chuyện/hình ảnh trung tâm): {concept}

YÊU CẦU LYRICS:
- Lời tiếng Việt, mới hoàn toàn, không sáo rỗng, một hình ảnh trung tâm.
- BẮT BUỘC có section labels TIẾNG ANH trong ngoặc vuông cho từng phần, mỗi label một dòng, kèm mô tả nhạc cụ/động lực, ví dụ:
  [Intro - solo cello, distant waves]
  [Verse 1 - restrained lead vocal]
  [Pre-Chorus - strings rise, tension builds]
  [Chorus - big hook, choir + brass, full drums]
  [Verse 2 - denser imagery]
  [Bridge - stripped, emotional turn / cao trào]
  [Final Chorus - stacked harmonies, climax]
  [Outro - motif returns, clean fade]
- Tối thiểu 6 section, phải có Intro, Chorus, và ít nhất một [Hook] hoặc [Chorus] đóng vai hook rõ ràng.
- BẮT BUỘC có một hook bắt tai kiểu: {hook_type}.

YÊU CẦU STYLE (prompt nhạc cho Suno, viết bespoke riêng bài này):
- 1 đoạn giàu chi tiết: thể loại + BPM/nhịp + nhạc cụ cụ thể + tiến trình arrangement (verse->chorus->bridge->outro) + mood + chất lượng production.
- Đúng chất câu chuyện của bài, KHÔNG generic, KHÔNG dùng chung cho bài khác.
- BẮT BUỘC mô tả rõ HOOK trong style (loại hook: {hook_type}), nêu hook nằm ở đâu và bằng nhạc cụ/giọng gì.

Khác hoàn toàn bài liền trước (chủ đề, hình ảnh, hook, style):
<<<{prev if prev else '(chưa có)'}>>>

CHỈ trả JSON duy nhất, không kèm ```:
{{"title":"...","lyrics":"...(có [Section] tiếng Anh)...","style":"...(bespoke)..."}}"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genre", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--concept", required=True)
    ap.add_argument("--genre-brief", default="")
    ap.add_argument("--prev-file", default="")
    ap.add_argument("--out-lyrics", required=True)
    ap.add_argument("--out-style", required=True)
    a = ap.parse_args()
    prev = ""
    if a.prev_file and Path(a.prev_file).exists():
        prev = Path(a.prev_file).read_text(encoding="utf-8")[:2000]
    for attempt in range(4):
        hook_type = _rnd.choice(HOOK_TYPES)
        title, lyrics, style, used = call_llm(build_prompt(a.genre, a.title, a.concept, a.genre_brief, prev, hook_type))
        if not lyrics or not style:
            continue
        Path(a.out_lyrics).write_text(lyrics, encoding="utf-8")
        Path(a.out_style).write_text(style, encoding="utf-8")
        s_ok = guard_structure(Path(a.out_lyrics))
        st_ok = guard_style(style)
        if s_ok and st_ok:
            print(json.dumps({"title": title or a.title, "lyrics_file": a.out_lyrics,
                              "style_file": a.out_style, "structure_ok": True,
                              "style_ok": True, "model": used}, ensure_ascii=False))
            return 0
    print(json.dumps({"error": "failed to produce clean structured song", "structure_ok": False, "style_ok": False}, ensure_ascii=False))
    return 3

if __name__ == "__main__":
    raise SystemExit(main())
