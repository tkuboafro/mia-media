#!/usr/bin/env python3
"""空いたヒーロー／見出し枠を、手で決めた検索語で埋め直す（自動配置が検品を通らなかった時の後処理）。
使い方: fillslot.py job.json   job = {"slug":..., "hero": {"caption":..., "queries":[...], "prompt":...},
        "slots": [{"heading":"見出しの先頭数文字", "caption":..., "queries":[...], "prompt":...}]}
各枠: queries を順に検索 → 候補を Opus 検品 → 通ったものを採用。無ければ prompt で最大3回生成（毎回検品）。"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sns"))
import stock, genimg, notion
HOME = os.path.expanduser("~/mia-media")

def find(queries, prompt, caption):
    desc = f"{caption} / {' ; '.join(queries)}"
    seen = set()
    for q in queries:
        for c in stock.search(q, 4):
            if c["url"] in seen: continue
            seen.add(c["url"])
            if stock.vet(c["url"], desc): stock.track(c); return c["url"], c["credit"]
    for _ in range(3):
        u = genimg.try_generate(prompt)
        if u and stock.vet(u, desc): return u, genimg.CREDIT_JA
    return None, None

def main(job):
    slug = job["slug"]; mp = f"{HOME}/data/article_{slug}.json"; meta = json.load(open(mp)); ja = meta["ja"]
    if job.get("hero") and not meta.get("hero"):
        h = job["hero"]; u, cr = find(h["queries"], h["prompt"], h["caption"])
        if u: meta["hero"], meta["heroAlt"], meta["heroCredit"] = u, h["caption"], cr; ja["hero_caption"] = h["caption"]
        print(f"{slug[:40]} hero: {'OK '+cr if u else 'なし'}", flush=True)
    lines = ja["body_md"].splitlines()
    for s in job.get("slots", []):
        idx = next((i for i, l in enumerate(lines) if l.startswith("## ") and l[3:].strip().startswith(s["heading"])), None)
        if idx is None: print(f"{slug[:40]} slot {s['heading']}: 見出しが無い"); continue
        nxt = next((x for x in lines[idx + 1:idx + 3] if x.strip()), "")
        if nxt.startswith("[["): print(f"{slug[:40]} slot {s['heading']}: 既に画像あり"); continue
        u, cr = find(s["queries"], s["prompt"], s["caption"])
        if u: lines[idx + 1:idx + 1] = ["", f"[[image:{u}|{s['caption']}|{cr}]]", ""]
        print(f"{slug[:40]} slot {s['heading']}: {'OK '+cr if u else 'なし'}", flush=True)
    ja["body_md"] = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
    notion.replace_body(meta["notion_page"], meta)

if __name__ == "__main__":
    main(json.load(open(sys.argv[1])))
