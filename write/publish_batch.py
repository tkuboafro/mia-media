#!/usr/bin/env python3
"""確認待ちの記事を、自分で再レビューしてから公開する（久保さん 2026-10-26「俺のレビューはいらない。投稿前に自分で再レビュー、直しが要れば直して公開してよい。ソース記事が古い順に」）。
- 順番: ソース記事の公開日（row.published）が古い順。
- 再レビュー（Sonnet）: 今日の時点で過ぎた予定の時制、ソース要約との矛盾、お酒の広告として不適切な表現、誤字だけを直す。[[...]] のメディア行は変えない（変わったら修正を捨てる）。
- 翻訳は Sonnet。サイト上の日付（pubDate）はソース記事の日付にする。
- まとめて公開: BATCH 本ずつ md を書き、ビルド1回・push1回（GitHub Pages の更新回数を抑える）。
- 公開後 Notion: ステータス=投稿済み、投稿URL=日本語版、自動レビューで直した場合は承認コメントに要点。
- 3回続けてモデルが応答しなければ止める（使用上限）。次回の実行で続きから。
使い方: publish_batch.py [--limit N] [--batch 20]"""
import datetime as dt, json, os, re, subprocess, sys, time
HOME = os.path.expanduser("~/mia-media")
sys.path.insert(0, HOME); sys.path.insert(0, os.path.join(HOME, "write")); sys.path.insert(0, os.path.join(HOME, "sns"))
import publish, notion
from translate import translate
from article import region_en
MEDIA = re.compile(r"^\[\[[a-z]+:[^\]]*\]\]\s*$", re.M)

REVIEW = """あなたは The Sake Wire（アムステルダム発、日本の酒のニュースサイト）の校閲者です。今日は {today} です。
次の日本語記事を公開前に最終確認してください。ソース記事の公開日は {src_date}、ソースは「{src_name}」。
ソースの要約: {summary}

直すのは次の4つだけです。
1. 時制・時期: 今日の時点ですでに過ぎた予定（イベント、発売、受付・予約の期限、「今月」「来週」「今後」など）を、過去のこととして正しく書き直す。終わった行動への呼びかけ（「申し込める」「訪れてみては」など）は削るか過去形にする。
2. ソースの要約と明確に矛盾する数字・名前・日付。要約に無いだけの情報は消さない。
3. 断定しすぎ・誇張、健康効果、飲酒をあおる表現（酒類広告として不適切なもの）。
4. 誤字脱字、文の破綻。
それ以外（内容、文体、見出しの構成）は変えない。[[ で始まる行は一字も変えず、位置も動かさない。

【記事】
タイトル: {title}
リード: {lead}
本文:
{body}

JSONだけを返す: {{"changed": true|false, "title": "", "lead": "", "body_md": "", "notes": "何を直したか（日本語1〜2文。直していなければ空）"}}
changed が false なら title/lead/body_md は空でよい。true なら3つとも全文を返す。"""

def ask(p, model="sonnet"):
    for wait in (0, 60, 300):
        if wait: time.sleep(wait)
        r = subprocess.run(["claude", "-p", p, "--output-format", "json", "--model", model, "--allowedTools", ""], capture_output=True, text=True, timeout=900)
        try:
            raw = json.loads(r.stdout).get("result", ""); return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception: continue
    raise RuntimeError("model gave no JSON (usage limit?)")

def review(meta):
    ja, row = meta["ja"], meta["row"]
    r = ask(REVIEW.format(today=dt.date.today().isoformat(), src_date=(row.get("published") or "")[:10], src_name=row.get("source") or "",
                          summary=row.get("summary_ja") or row.get("title") or "", title=ja["title"], lead=ja.get("lead", ""), body=ja["body_md"]))
    if not r.get("changed") or not r.get("body_md") or not r.get("title"): return None
    if MEDIA.findall(r["body_md"]) != MEDIA.findall(ja["body_md"]): return "media-mismatch"   # メディア行を触った修正は捨てる
    ja.update({"title": r["title"].strip(), "lead": (r.get("lead") or ja.get("lead", "")).strip(), "body_md": r["body_md"].strip()})
    return (r.get("notes") or "自動レビューで修正").strip()

def run(*a, cwd=HOME): return subprocess.run(a, cwd=cwd, capture_output=True, text=True)

def targets():
    body = {"filter": {"and": [{"property": "チャネル", "select": {"equals": "Journal"}},
            {"or": [{"property": "ステータス", "select": {"equals": s}} for s in ("確認待ち", "承認")]}]}, "page_size": 100}
    out = []
    while True:
        r = notion.api("POST", f"/data_sources/{notion.DS}/query", body)
        for p in r["results"]:
            slug = notion.prop_text(p, "記事キー").strip(); mp = f"{HOME}/data/article_{slug}.json"
            if slug and os.path.exists(mp):
                out.append(((json.load(open(mp))["row"].get("published") or "9999")[:10], slug, p["id"]))
        if not r.get("has_more"): break
        body["start_cursor"] = r["next_cursor"]
    return sorted(out)

def prepare(slug):
    mp = f"{HOME}/data/article_{slug}.json"; meta = json.load(open(mp))
    note = None
    if not meta.get("auto_reviewed"):
        note = review(meta); meta["auto_reviewed"] = time.strftime("%Y-%m-%d")
        if note == "media-mismatch": note = None
    src_date = (meta["row"].get("published") or "")[:10]
    if re.match(r"\d{4}-\d{2}-\d{2}$", src_date): meta["date"] = src_date
    meta["regionEn"] = region_en(meta["row"].get("region"))
    import hashlib
    ja = meta["ja"]; src = hashlib.sha1(json.dumps([ja.get("title"), ja.get("lead"), ja.get("body_md")], ensure_ascii=False).encode()).hexdigest()
    if not (meta.get("translations") and meta.get("translated_from") == src):
        meta["translations"] = translate(ja, model="sonnet", hero_alt=meta.get("heroAlt") or ""); meta["translated_from"] = src
    imgs = publish.rehost_generated(slug, meta); ja, tr = meta["ja"], meta["translations"]
    json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
    paths = [publish.write_md("ja", slug, meta, ja["title"], ja["lead"], ja["body_md"])]
    for L in ("en", "nl", "de", "es"): paths.append(publish.write_md(L, slug, meta, tr[L]["title"], tr[L]["description"], tr[L]["body_md"]))
    return paths + imgs, note

def ship(paths, n):
    b = run("npm", "run", "build", cwd=publish.SITE)
    if b.returncode != 0: print(b.stdout[-1500:], b.stderr[-800:], flush=True); return False
    run("git", "pull", "-q", "--rebase", "--autostash"); run("git", "add", *paths)
    run("git", "-c", "user.name=MIA Journal bot", "-c", "user.email=tkubo@danshiko.com", "commit", "-q", "-m", f"journal: publish {n} articles")
    for i in range(6):   # 他のジョブ（SNS カード・HANDOFF 更新）と push がぶつかることがあるので、間を空けて取り直す
        p = run("git", "push", "-q")
        if p.returncode == 0: return True
        print("push retry", i, p.stderr.strip()[:160], flush=True)
        time.sleep(20 * (i + 1)); run("git", "pull", "-q", "--rebase", "--autostash")
    return False

if __name__ == "__main__":
    me = os.getpid()
    others = [l for l in subprocess.run(["pgrep", "-f", "write/publish_batch.py"], capture_output=True, text=True).stdout.split() if int(l) != me]
    if others: print("another publish_batch is running — skip"); sys.exit(0)
    a = sys.argv[1:]
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else None
    batch = int(a[a.index("--batch") + 1]) if "--batch" in a else 20
    todo = targets()
    if limit: todo = todo[:limit]
    print(time.strftime("%m-%d %H:%M"), "to publish:", len(todo), flush=True)
    fails = 0; total = 0
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]; paths = []; done = []
        for src_date, slug, pid in chunk:
            try:
                p, note = prepare(slug); paths += p; done.append((slug, pid, note)); fails = 0
            except Exception as e:
                fails += 1; print("!!", slug, str(e)[:160], flush=True)
                if fails >= 3: break
        if done and ship(paths, len(done)):
            for slug, pid, note in done:
                props = {"ステータス": {"select": {"name": "投稿済み"}}, "投稿URL": {"url": f"{publish.PUB}/ja/{slug}/"}}
                if note: props["承認コメント"] = {"rich_text": notion.rt(("自動レビューで修正: " + note)[:1900])}
                notion.api("PATCH", f"/pages/{pid}", {"properties": props})
            total += len(done); print(time.strftime("%m-%d %H:%M"), f"published {total}/{len(todo)}", flush=True)
        elif done: print("!! ship failed — stop", flush=True); break
        if fails >= 3: print("ABORT: 3 consecutive failures", flush=True); break
    print("DONE", total, flush=True)
