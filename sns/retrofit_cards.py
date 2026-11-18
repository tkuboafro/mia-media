#!/usr/bin/env python3
"""まだ IG に出ていない記事の IG カードを、写真あり・重複なしに作り直す（2026-11-19 久保さん「サムネが無い・全く一緒、にならないように」）。

対象: Notion「MIA SNS投稿管理」の Journal 行のうち IG状態が投稿済みでないもの（＝これから mia_sns が IG に出すもの）。
mia_sns と同じ順番（ソースの古い順）に処理し、文字だけのカード・他の記事と同じ写真のカードだけ作り直す。
5 枚ごとに commit・push（GitHub Pages の https://sakewire.com/sns/<slug>-ig.png が差し替わる）。
使い方: python3 sns/retrofit_cards.py [--dry] [--limit N]   （NOTION_TOKEN・PEXELS_KEY・UNSPLASH_KEY は secrets.env か環境変数）"""
import json, os, re, subprocess, sys, time
import requests
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, "write"))
import photos, card_photo, make_card, stock

DS = "fb94f323-ceec-4ef9-93bd-96e2fde80ab8"
DRY = "--dry" in sys.argv
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10 ** 6
CAT = {v: k for k, v in make_card.CAT.items()}


def token():
    return os.environ.get("NOTION_TOKEN") or stock._env("NOTION_TOKEN")


def query(flt):
    body, out = {"filter": flt, "page_size": 100}, []
    while True:
        r = requests.post(f"https://api.notion.com/v1/data_sources/{DS}/query", json=body, timeout=60,
                          headers={"Authorization": "Bearer " + token(), "Notion-Version": "2025-09-03"}).json()
        out += r["results"]
        if not r.get("has_more"): return out
        body["start_cursor"] = r["next_cursor"]


def ptext(p, k):
    v = p["properties"].get(k) or {}
    return "".join(x.get("plain_text", "") for x in (v.get("rich_text") or v.get("title") or []))


def psel(p, k):
    return ((p["properties"].get(k) or {}).get("select") or {}).get("name")


def fm(slug):
    t = open(os.path.join(photos.ARTS, "en", slug + ".md")).read().split("\n---", 1)[0]
    g = lambda k: (re.search(rf'^{k}:\s*"?(.*?)"?\s*$', t, re.M) or [None, ""])[1]
    tags = json.loads(g("tags") or "[]") if (g("tags") or "").startswith("[") else []
    return {"slug": slug, "hero": g("hero") or None, "heroCredit": g("heroCredit"), "heroAlt": g("heroAlt"), "regionEn": g("regionEn"),
            "pubDate": g("pubDate"), "tags": tags, "row": {"category": g("category")},
            "translations": {"en": {"title": json.loads('"' + g("title") + '"'), "description": json.loads('"' + g("description") + '"')}},
            "ja": {"title": ""}}


def credit_ok(m):
    c = m.get("heroCredit") or ""
    # 英語版の md は "Photo: …"、元原稿は "写真: …"。プレス画像（Image: / 画像提供）と AI は使わない
    return bool(m.get("hero")) and (c.startswith("Photo") or c.startswith("写真")) and "AI" not in c


def ship(paths, n):
    if DRY or not paths: return
    subprocess.run(["git", "pull", "-q", "--rebase", "--autostash"], cwd=REPO)
    subprocess.run(["git", "add", *[os.path.realpath(x) for x in paths]], cwd=REPO, check=True)
    subprocess.run(["git", "-c", "user.name=MIA Journal bot", "commit", "-q", "-m", f"sns: IG カード {n} 枚を写真あり・重複なしで作り直し"], cwd=REPO, check=True)
    for i in range(5):
        if subprocess.run(["git", "push", "-q"], cwd=REPO).returncode == 0: return
        time.sleep(15 * (i + 1)); subprocess.run(["git", "pull", "-q", "--rebase", "--autostash"], cwd=REPO)
    raise SystemExit("push できない")


def main():
    rows = query({"and": [{"property": "チャネル", "select": {"equals": "Journal"}},
                          {"property": "ステータス", "select": {"equals": "投稿済み"}}]})
    dates = json.load(open(os.path.join(HERE, "src_dates.json")))
    todo = []
    for p in rows:
        slug = ptext(p, "記事キー").strip()
        if psel(p, "IG状態") in ("投稿済み", "予約済み") or not ptext(p, "IGキャプション").strip(): continue
        if not os.path.exists(os.path.join(photos.ARTS, "en", slug + ".md")): continue
        todo.append((dates.get(slug) or fm(slug)["pubDate"] or "9999", slug))
    # mia_sns と同じ順（サイト公開 3 日以内は新しい順で先、残りはソースの古い順）。新着のカードから先に直す
    import datetime as dt
    recent = (dt.datetime.utcnow() - dt.timedelta(days=3)).strftime("%Y-%m-%d")
    todo.sort(key=lambda x: (0, -int(x[1][:10].replace("-", "")), x[1]) if re.match(r"\d{4}-\d{2}-\d{2}", x[1]) and x[1][:10] >= recent else (1, x[0], x[1]))
    idx = photos.hero_index(); led = photos.ledger()
    need = []
    for _, slug in todo:
        m = fm(slug)
        if slug in led: continue
        dup = len(idx.get(photos.pid(m["hero"]), [])) > 1 if m["hero"] else False
        if not credit_ok(m) or dup: need.append((slug, "dup" if dup else "nophoto"))
    print(f"未投稿 {len(todo)} 本・作り直し {len(need)} 本（写真なし {sum(1 for x in need if x[1]=='nophoto')}・重複 {sum(1 for x in need if x[1]=='dup')}）", flush=True)
    batch, done = [], 0
    for slug, why in need[:LIMIT]:
        m = fm(slug)
        m["heroCredit"] = ""   # ヒーローは使わず、重複なしの写真を台帳に取る
        try:
            if DRY: print("dry", slug, why, card_photo.choose(m, idx, dry=True)[1]); continue
            try: png, _ = make_card.render(m)
            except card_photo.NoPhoto:   # 写真 API の回数制限（Pexels 200/時・Unsplash 50/時）で候補が空のことがある → 10 分待って 1 回だけ
                time.sleep(600); png, _ = make_card.render(m)
            batch += [png, photos.LEDGER]; done += 1
            print("ok", slug, why, photos.ledger()[slug]["credit"], flush=True)
        except Exception as e:
            print("!!", slug, str(e)[:150], flush=True)
        if len(batch) >= 10: ship(sorted(set(batch)), done); batch, done = [], 0
    ship(sorted(set(batch)), done)


if __name__ == "__main__":
    main()
