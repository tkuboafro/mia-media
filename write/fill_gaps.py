#!/usr/bin/env python3
"""確認待ち原稿の「画像の抜け」を埋める（2026-10-10 久保さん: 一昨日以前の原稿の画像を再チェック）。
本文は変えない。ヒーロー無し・メディアの無い見出しだけを、引用（元記事の画像・関連 YouTube）→ フリー素材（Opus 検品）の順で埋める。
AI 生成はしない。合う画像が無ければ空けたまま（間違った画像より空の方がよい）。
入力: data/audit/media_audit.json（audit_media.py）。使い方: fill_gaps.py [slug ...] [--limit N]"""
import json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sns"))
import notion, stock, media as mediamod
from article_ja import brand_terms
HOME = os.path.expanduser("~/mia-media")
MEDIA_LINE = re.compile(r"^\[\[(?:image|youtube|x|instagram):[^\]]*\]\]\s*$", re.M)

PROMPT = """日本語ニュース記事の「画像が無い場所」に入れる画像を決めます。本文は変えません。

【記事タイトル】{title}
【リード】{lead}

【画像が無い場所】
{slots}

{media}

各場所について、上の「利用できるメディア」に内容が明確に合うものがあれば番号を選ぶ（同じ番号は1回だけ。"site" 種別は選ばない）。
無ければ、フリー素材サイトで探す英語の検索語（一般的な2〜4語。例: "sake brewery tanks", "rice paddy autumn", "whisky glass bar"）を書く。
実在の特定の人物・建物を探す検索語は書かない。キャプションは写したいものを具体的な日本語で（出典は書かない）。
JSONだけを返す: {{"slots":[{{"id":"場所のID","media":番号またはnull,"query":"英語またはnull","caption":"日本語"}}]}}"""

def ask(p):
    for wait in (0, 60, 300):
        if wait: time.sleep(wait)
        r = subprocess.run(["claude", "-p", p, "--output-format", "json", "--model", "sonnet", "--allowedTools", ""], capture_output=True, text=True, timeout=600)
        try:
            raw = json.loads(r.stdout).get("result", "")
            return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception: continue
    raise RuntimeError("model gave no JSON (usage limit?)")

def section_text(body, head):
    m = re.search(r"^## " + re.escape(head) + r"\s*\n([\s\S]*?)(?=^## |\Z)", body, re.M)
    return re.sub(r"\s+", " ", MEDIA_LINE.sub("", m.group(1)))[:280] if m else ""

def fill(r):
    slug = r["slug"]; mp = os.path.join(HOME, "data", f"article_{slug}.json"); meta = json.load(open(mp)); ja = meta["ja"]
    body = ja["body_md"]
    # Notion 側の本文が手直しされていたら触らない（上書き事故を防ぐ）
    now = notion.read_ja(r["page"])
    def plain(md): return re.sub(r"\s+", "", MEDIA_LINE.sub("", md or ""))
    if plain(now.get("body_md")) and plain(now["body_md"]) != plain(body):
        return f"{slug}: SKIP Notion の本文が原稿と違う（手直しあり？）"
    slots = []
    if not meta.get("hero"): slots.append(("hero", "記事冒頭の大きな写真（記事全体を表す）"))
    for i, h in enumerate(r["h2_without_media"]): slots.append((f"h{i}", f"見出し「{h}」の直後 — 内容: {section_text(body, h)}"))
    if not slots: return f"{slug}: 抜けなし"
    used = set(re.findall(r"\[\[(?:image|youtube|x|instagram):([^\]|]+)", body)) | {meta.get("hero")}
    try: medias = [m for m in mediamod.collect(meta["row"], brand_terms(meta["row"])) if m["url"] not in used and m["type"] in ("image", "youtube")]
    except Exception: medias = []
    plan = ask(PROMPT.format(title=ja["title"], lead=ja["lead"], slots="\n".join(f"- ID {k}: {d}" for k, d in slots), media=mediamod.as_prompt(medias)))
    got = {"hero": 0, "sec": 0, "quote": 0, "stock": 0}; heads = {f"h{i}": h for i, h in enumerate(r["h2_without_media"])}
    for s in plan.get("slots", []):
        sid = s.get("id"); cap = (s.get("caption") or "").strip(); line = None; url = cred = None
        m = None
        try: m = medias[int(s["media"]) - 1] if s.get("media") else None
        except Exception: m = None
        if m and m["url"] not in used:
            if m["type"] == "image": url, cred = m["url"], m.get("credit", "")
            elif sid != "hero": line = f"[[youtube:{m['url']}]]"
            if url or line: got["quote"] += 1; used.add(m["url"])
        if not (url or line) and s.get("query"):
            c = stock.pick(s["query"], f"{cap} / {s['query']}")
            if c and c["url"] not in used: url, cred = c["url"], c["credit"]; got["stock"] += 1; used.add(c["url"])
        if not (url or line): continue
        if sid == "hero" and url:
            meta["hero"], meta["heroAlt"], meta["heroCredit"] = url, cap, cred
            ja["hero_image"], ja["hero_caption"], ja["hero_credit"] = url, cap, cred; got["hero"] += 1
        elif sid in heads:
            line = line or f"[[image:{url}|{cap}|{cred}]]"
            body = re.sub(r"(^## " + re.escape(heads[sid]) + r"[ \t]*\n)", lambda mm: mm.group(1) + "\n" + line + "\n", body, count=1, flags=re.M); got["sec"] += 1
    if got["hero"] or got["sec"]:
        ja["body_md"] = body; meta.setdefault("fixes", []).append({"date": "2026-10-10", "fill_gaps": got})
        json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
        notion.replace_body(r["page"], meta)
    left = len(r["h2_without_media"]) - got["sec"]
    return f"{slug}: ヒーロー {'+1' if got['hero'] else ('なし' if not meta.get('hero') else 'あり')} / 見出し +{got['sec']}（残り空き {left}）/ 引用 {got['quote']} 素材 {got['stock']}"

if __name__ == "__main__":
    A = json.load(open(os.path.join(HOME, "data", "audit", "media_audit.json")))
    rows = [r for r in A["rows"] if "page" in r and (not r["hero"] or r["h2_without_media"])]
    args = [a for a in sys.argv[1:] if not a.startswith("--") and not a.isdigit()]
    if args: rows = [r for r in rows if r["slug"] in args]
    if "--limit" in sys.argv: rows = rows[:int(sys.argv[sys.argv.index("--limit") + 1])]
    done_f = os.path.join(HOME, "data", "audit", "fill_gaps_done.txt")
    done = set(open(done_f).read().split()) if os.path.exists(done_f) else set()
    fails = 0
    for r in rows:
        if r["slug"] in done: continue
        try:
            print(fill(r), flush=True); fails = 0
            open(done_f, "a").write(r["slug"] + "\n")
        except Exception as e:
            fails += 1; print(f"!! {r['slug']}: {str(e)[:200]}", flush=True)
            if fails >= 5: print("ABORT: 5 consecutive failures", flush=True); break
