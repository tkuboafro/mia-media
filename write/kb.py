#!/usr/bin/env python3
"""参考資料コーパス（SAKE Street 全513記事、data/sakestreet/articles/articles.json）。
記事を書くときに関連する解説を3本まで渡し、使ったら出典に入れさせる。丸写しはしない（プロンプトで禁止）。"""
import json, os, re, sqlite3
HOME = os.path.expanduser("~/mia-media")
SRC = os.path.join(HOME, "data", "sakestreet", "articles", "articles.json")
DB = os.path.join(HOME, "data", "kb.sqlite")

def build():
    if not os.path.exists(SRC): return False
    con = sqlite3.connect(DB); c = con.cursor()
    c.execute("DROP TABLE IF EXISTS doc"); c.execute("CREATE VIRTUAL TABLE doc USING fts5(url, lang, title, published, text, tokenize='trigram')")
    for r in json.load(open(SRC)):
        c.execute("INSERT INTO doc VALUES (?,?,?,?,?)", (r["url"], r.get("lang"), r.get("title") or "", r.get("published") or "", r.get("text") or ""))
    con.commit(); con.close(); return True

def search(query, lang="ja", k=3, excerpt=700):
    if not os.path.exists(DB) and not build(): return []
    con = sqlite3.connect(DB); c = con.cursor()
    terms = [t for t in re.findall(r"[一-龠ぁ-んァ-ンA-Za-z0-9]{2,}", query) if t not in ("日本酒", "について", "する", "した", "こと")][:8]
    if not terms: return []
    q = " OR ".join(f'"{t}"' for t in terms)
    try:
        rows = c.execute("SELECT url, title, published, snippet(doc, 4, '', '', '…', 60), text FROM doc WHERE doc MATCH ? AND lang = ? ORDER BY rank LIMIT ?", (q, lang, k)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    con.close()
    out = []
    for url, title, pub, snip, text in rows:
        i = max(0, text.find(snip.strip("…")[:20]) - 100) if snip else 0
        out.append({"url": url, "title": title.replace(" | SAKE Street", ""), "published": pub, "excerpt": text[i:i + excerpt].strip()})
    return out

def as_prompt(items):
    if not items: return ""
    s = "\n【参考資料（背景説明の裏取り用。文章をそのまま写さない。内容を使った場合は出典に「SAKE Street」として URL を必ず入れる）】\n"
    for it in items:
        s += f"- {it['title']}（{it['published']}） {it['url']}\n  {it['excerpt']}\n"
    return s

if __name__ == "__main__":
    import sys; print(build()); [print(x["title"], x["url"]) for x in search(sys.argv[1] if len(sys.argv) > 1 else "精米歩合 純米吟醸")]
