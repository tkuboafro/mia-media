#!/usr/bin/env python3
"""記事ごとの SNS 投稿文を作って Notion「MIA SNS投稿管理」の列に入れる（2026-10-25 久保さん依頼）。
列: 「IGキャプション」（@thesakewire 用）と「X投稿文（Threads共用）」（@TheSakeWire 用。Threads にも同じ文を使う）。
対象: チャネル=Journal で ステータスが 確認待ち／承認／投稿済み の行（見送りは除く）。既に両方入っている行は飛ばす（再開可）。
本文は記事の日本語原稿だけを根拠に英語で書く（記事に無い事実を足さない）。ページ本文（ブロック）は触らない。
使い方: sns_texts.py [--limit N] [--batch 6] [--redo]"""
import json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notion
HOME = os.path.expanduser("~/mia-media"); SITE = "https://sakewire.com"
COL_IG, COL_X = "IGキャプション", "X投稿文（Threads共用）"
TAIL = "Drink responsibly. 18+"
MEDIA = re.compile(r"^\[\[[a-z]+:[^\]]*\]\]\s*$", re.M)

PROMPT = """You write social posts for The Sake Wire, an English-language news site in Amsterdam about Japanese sake, shochu, whisky, wine and beer, read in Europe.
For EACH article below write two texts in British English, using ONLY facts stated in that article (never add numbers, names, awards or claims that are not in it; no prices unless the article states them).

1. "x": one post for X (also reused on Threads). Plain news tone, no hype, no emoji. Structure: one-sentence headline-style hook, then one sentence of the most useful detail for a European reader. Max 190 characters for these two sentences together. Do NOT include the URL, hashtags or "18+" — the system adds them.
2. "ig": an Instagram caption. First line = a hook under 90 characters. Then 2–3 short paragraphs (what happened, why it matters, what a reader in Europe can do or look for). Then the line "Read the full story — link in bio." Then "Source: <publisher name as given>". Max 900 characters before hashtags. Do NOT add hashtags or "18+" — the system adds them.
Also return "tags": 6 short CamelCase hashtag words without '#', relevant to the article (e.g. Sake, Akita, JapaneseWhisky, CraftBeer, JapaneseWine, Shochu, SakeBrewery, Umeshu, Gin).

Return ONLY JSON: {{"<key>": {{"x": "...", "ig": "...", "tags": ["...", ...]}}, ...}} with exactly the keys given.

{articles}"""

def article_block(key, m):
    ja = m["ja"]; tr = (m.get("translations") or {}).get("en") or {}
    body = MEDIA.sub("", ja.get("body_md") or "").strip()
    src = ", ".join(s.get("name") or "" for s in (ja.get("sources") or []) if s.get("name"))
    en = f"\nENGLISH TITLE (published): {tr['title']}" if tr.get("title") else ""
    return f"=== KEY: {key} ===\nTITLE (JA): {ja['title']}{en}\nLEAD (JA): {ja.get('lead','')}\nSOURCE: {src}\nBODY (JA):\n{body[:3500]}\n"

def ask(p):
    for wait in (0, 60, 300):
        if wait: time.sleep(wait)
        r = subprocess.run(["claude", "-p", p, "--output-format", "json", "--model", "sonnet", "--allowedTools", ""], capture_output=True, text=True, timeout=900)
        try:
            raw = json.loads(r.stdout).get("result", ""); return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception: continue
    raise RuntimeError("model gave no JSON (usage limit?)")

def tags_str(tags, n):
    out = []
    for t in tags:
        t = re.sub(r"[^A-Za-z0-9]", "", t or "")
        if t and t.lower() not in {x.lower() for x in out}: out.append(t)
    base = ["TheSakeWire"] if n > 2 else []
    return " ".join("#" + t for t in (base + out)[:n])

def build_x(text, slug, tags):
    url = f"{SITE}/en/{slug}/?utm_source=x&utm_medium=social&utm_campaign={slug}"
    t = tags_str(tags, 2); text = re.sub(r"\s+\n", "\n", text.strip())
    room = 280 - 23 - len(TAIL) - len(t) - 4   # URL は 23 字換算、改行4つ
    if len(text) > room: text = text[:room - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return f"{text}\n{url}\n{t}\n{TAIL}"

def build_ig(text, tags):
    text = text.strip()
    if len(text) > 1500: text = text[:1500].rsplit("\n", 1)[0]
    return f"{text}\n\n{tags_str(tags, 8)}\n{TAIL}"

def rt_long(s):  # Notion の rich_text は1要素2000字まで
    return [{"type": "text", "text": {"content": s[i:i + 1900]}} for i in range(0, len(s), 1900)] or [{"type": "text", "text": {"content": ""}}]

def ensure_columns():
    ds = notion.api("GET", f"/data_sources/{notion.DS}")
    add = {c: {"rich_text": {}} for c in (COL_IG, COL_X) if c not in ds["properties"]}
    if add: notion.api("PATCH", f"/data_sources/{notion.DS}", {"properties": add})
    return list(add)

def targets(redo=False):
    body = {"filter": {"and": [{"property": "チャネル", "select": {"equals": "Journal"}},
            {"or": [{"property": "ステータス", "select": {"equals": s}} for s in ("確認待ち", "承認", "投稿済み")]}]}, "page_size": 100}
    out = []
    while True:
        r = notion.api("POST", f"/data_sources/{notion.DS}/query", body)
        for p in r["results"]:
            slug = notion.prop_text(p, "記事キー").strip()
            filled = notion.prop_text(p, COL_IG).strip() and notion.prop_text(p, COL_X).strip()
            if slug and (redo or not filled) and os.path.exists(f"{HOME}/data/article_{slug}.json"): out.append((p["id"], slug))
        if not r.get("has_more"): return out
        body["start_cursor"] = r["next_cursor"]

if __name__ == "__main__":
    a = sys.argv[1:]
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else None
    batch = int(a[a.index("--batch") + 1]) if "--batch" in a else 6
    print("added columns:", ensure_columns(), flush=True)
    todo = targets("--redo" in a)
    if limit: todo = todo[:limit]
    print("rows to write:", len(todo), flush=True)
    done = fails = 0
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]; metas = {s: json.load(open(f"{HOME}/data/article_{s}.json")) for _, s in chunk}
        try:
            res = ask(PROMPT.format(articles="\n".join(article_block(s, metas[s]) for _, s in chunk))); fails = 0
        except Exception as e:
            fails += 1; print("!! batch", i, str(e)[:120], flush=True)
            if fails >= 3: print("ABORT: 3 consecutive failures", flush=True); break
            continue
        for pid, slug in chunk:
            g = res.get(slug)
            if not g or not g.get("x") or not g.get("ig"): print("!! missing", slug, flush=True); continue
            x = build_x(g["x"], slug, g.get("tags") or []); ig = build_ig(g["ig"], g.get("tags") or [])
            notion.api("PATCH", f"/pages/{pid}", {"properties": {COL_X: {"rich_text": rt_long(x)}, COL_IG: {"rich_text": rt_long(ig)}}})
            m = metas[slug]; m["sns"] = {"x": x, "ig": ig, "written": time.strftime("%Y-%m-%d")}
            json.dump(m, open(f"{HOME}/data/article_{slug}.json", "w"), ensure_ascii=False, indent=1)
            done += 1
        print(f"{time.strftime('%H:%M')} {done}/{len(todo)}", flush=True)
    print("DONE", done, flush=True)
