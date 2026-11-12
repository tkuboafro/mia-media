#!/usr/bin/env python3
"""The Sake Wire 日次記事作成（クラウド版）。Sub の run_daily.sh＋毎朝の自動公開（com.danshiko.mia-autopublish）の後継。
2026-11-12 久保さん「記事作成の仕組み作って」。Sub が復旧不能になり、記事が 10/28 で止まっていた。

毎朝のスケジュール済みクラウドセッションが `python3 cloud/daily.py` を実行する。ローカルの状態ファイルは持たない
（使用済み判定は公開済み記事 md から毎回作り直す）。手順:
  1. 準備   ~/mia-media → このリポジトリ、data/ 作成、secrets.env を Secret Manager（danshikolab）から作る
  2. 収集   Drive「MIA-NEWS（Grok 自動収集）」の MIA-NEWS_*.json（Grok の自動実行が毎朝置く）→ data/backlog.jsonl
  3. 使用済み 公開済み記事（ja md）の出典 URL・出典見出し → data/used_urls.txt と data/article_pub-*.json（pick.py の重複判定用）
  4. 選定   pick.ranked() の上位を AI（Sonnet）で「すでに記事にした出来事か」「候補同士で同じ出来事か」判定し、最大 N 本
  5. 執筆   article_ja（Opus）→ Notion に「確認待ち」で行を作る（Slack のレビュー依頼はしない＝10/26 久保さん「レビュー不要」）
  6. 公開   write/publish_batch.py（Sonnet で再レビュー＋4 言語翻訳・ビルド・push・Notion を「投稿済み」に）
  7. SNS 文 sns/sns_texts.py（X/Threads 共用文と IG キャプションを Notion へ）。投稿そのものは Otacon ハブ（Cloud Run）の mia_sns が拾う
使い方: python3 cloud/daily.py [--n 3] [--dry]   （--dry は 4 までで止め、選んだ候補を表示するだけ）
シークレットは名前だけ: GCP_SM_SA_KEY_JSON（環境変数・SM を読む SA 鍵）／SM: mia-notion-token, unsplash-access-key, pexels-api-key, GDRIVE_READONLY_TOKEN_JSON
"""
import datetime as dt, glob, json, os, re, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~/mia-media")
DATA = os.path.join(REPO, "data")
FOLDER = "1E9_QnNhULd9KkEfMqxlEwQPxzhZ9Gvuk"   # Drive「MIA-NEWS（Grok 自動収集）」
PROJECT = "danshikolab"


def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------- 1. 準備 ----------
def gcloud_ready():
    key = os.environ.get("GCP_SM_SA_KEY_JSON")
    if not key: raise SystemExit("GCP_SM_SA_KEY_JSON が無い（環境の設定を確認）")
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); f.write(key); f.close()
    env = {k: v for k, v in os.environ.items() if k != "CLOUDSDK_AUTH_ACCESS_TOKEN"}
    subprocess.run(["gcloud", "auth", "activate-service-account", f"--key-file={f.name}", "-q"], env=env, capture_output=True, check=True)
    os.unlink(f.name)
    return env


def sm(name, env):
    r = subprocess.run(["gcloud", "secrets", "versions", "access", "latest", f"--secret={name}", f"--project={PROJECT}"],
                       env=env, capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"SM {name}: {r.stderr.strip()[:200]}")
    return r.stdout.strip()


def setup():
    if os.path.realpath(HOME) != REPO:   # スクリプト群は ~/mia-media を前提にしている
        if os.path.islink(HOME) or not os.path.exists(HOME):
            if os.path.islink(HOME): os.unlink(HOME)
            os.symlink(REPO, HOME)
        else:
            raise SystemExit(f"{HOME} が別の実体で存在する")
    os.makedirs(DATA, exist_ok=True)
    env = gcloud_ready()
    sec = {"NOTION_TOKEN": sm("mia-notion-token", env), "UNSPLASH_KEY": sm("unsplash-access-key", env), "PEXELS_KEY": sm("pexels-api-key", env)}
    with open(os.path.join(REPO, "secrets.env"), "w") as f:   # .gitignore 済み
        for k, v in sec.items(): f.write(f"{k}={v}\n")
    os.environ.update(sec)
    if not os.path.isdir(os.path.join(REPO, "site", "node_modules")):
        subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=os.path.join(REPO, "site"), check=True, capture_output=True)
    for k, v in (("user.name", "MIA Journal bot"), ("user.email", "tkubo@danshiko.com")):
        subprocess.run(["git", "config", k, v], cwd=REPO)
    return env


# ---------- 2. 収集 ----------
def drive_token(env):
    import requests
    t = json.loads(sm("GDRIVE_READONLY_TOKEN_JSON", env))
    r = requests.post(t.get("token_uri", "https://oauth2.googleapis.com/token"), timeout=30,
                      data={"client_id": t["client_id"], "client_secret": t["client_secret"], "refresh_token": t["refresh_token"], "grant_type": "refresh_token"})
    return r.json()["access_token"]


def items_of(d):
    if isinstance(d, list): return d
    for k in ("items", "news", "rows"):
        if isinstance(d.get(k), list): return d[k]
    return next((v for v in d.values() if isinstance(v, list)), [])


def collect(env):
    import requests
    h = {"Authorization": "Bearer " + drive_token(env)}
    q = f"'{FOLDER}' in parents and name contains 'MIA-NEWS_' and trashed = false"
    files = requests.get("https://www.googleapis.com/drive/v3/files", headers=h, timeout=60,
                         params={"q": q, "fields": "files(id,name,createdTime)", "orderBy": "createdTime", "pageSize": 1000}).json().get("files", [])
    rows, seen = [], set()
    for f in files:
        try: d = requests.get(f"https://www.googleapis.com/drive/v3/files/{f['id']}?alt=media", headers=h, timeout=60).json()
        except Exception as e: log("!! 読めない", f["name"], str(e)[:80]); continue
        for r in items_of(d):
            u = (r.get("url") or "").strip()
            if not u or u in seen: continue
            seen.add(u); r.setdefault("why_eu", ""); r["grok_file"] = f["name"]; rows.append(r)
    with open(os.path.join(DATA, "backlog.jsonl"), "w") as out:
        for r in rows: out.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"収集: Drive {len(files)} ファイル → ニュース {len(rows)} 件")
    return rows


# ---------- 3. 使用済み ----------
def fm(path):
    t = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---", t, re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        k, _, v = line.partition(":")
        try: out[k.strip()] = json.loads(v.strip())
        except Exception: out[k.strip()] = v.strip()
    return out


def published():
    arts = []
    for p in glob.glob(os.path.join(REPO, "site", "src", "content", "articles", "ja", "*.md")):
        f = fm(p)
        urls = {f.get("sourceUrl")} | {s.get("url") for s in (f.get("sources") or []) if isinstance(s, dict)}
        arts.append({"slug": os.path.basename(p)[:-3], "date": f.get("pubDate", ""), "title": f.get("title", ""), "desc": f.get("description", ""),
                     "src_title": f.get("sourceTitle", ""), "akita": bool(f.get("akita")), "urls": {u for u in urls if u}})
    arts.sort(key=lambda a: a["date"])
    with open(os.path.join(DATA, "used_urls.txt"), "w") as f:
        for a in arts:
            for u in a["urls"]: f.write(u + "\n")
    for a in arts[-400:]:   # pick.used_topics()／akita_bonus() が読む形の控え（新しい順の mtime にする）
        p = os.path.join(DATA, f"article_pub-{a['slug']}.json")
        json.dump({"row": {"title": a["src_title"] or a["title"], "summary_ja": a["desc"], "akita": a["akita"]}}, open(p, "w"), ensure_ascii=False)
    for i, a in enumerate(arts[-10:]):
        t = time.time() - 600 + i; os.utime(os.path.join(DATA, f"article_pub-{a['slug']}.json"), (t, t))
    log(f"公開済み: {len(arts)} 本（最新 {arts[-1]['date'] if arts else '-'}）")
    return arts


# ---------- 4. 選定（AI で重複を外す） ----------
DEDUP = """あなたは日本の酒のニュースサイト The Sake Wire の編集デスクです。
【候補】のニュースのうち、記事にしてよいものを選んでください。外すのは次の 2 つだけです。
1. 【公開済みの記事】ですでに扱った出来事（同じ受賞・同じ商品発売・同じ発表。媒体や言い回しが違っても同じ出来事なら外す）
2. 候補同士で同じ出来事を報じているもの（残すのは 1 つだけ。番号の小さい方を残す）
別の年・別の回・別の商品なら別の出来事として残す。

【公開済みの記事（新しい順・見出し｜元記事の見出し）】
{pub}

【候補】
{cand}

JSONだけを返す: {{"keep": [残す候補の番号（小さい順）], "drop": {{"番号": "外す理由（日本語・短く。どの公開済み記事と同じか）"}}}}"""


def ask_json(p, model="sonnet"):
    for wait in (0, 60, 300):
        if wait: time.sleep(wait)
        r = subprocess.run(["claude", "-p", p, "--output-format", "json", "--model", model, "--allowedTools", ""], capture_output=True, text=True, timeout=900)
        try:
            raw = json.loads(r.stdout).get("result", "")
            return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        except Exception: continue
    raise RuntimeError("model gave no JSON")


def choose(arts, n):
    sys.path.insert(0, os.path.join(REPO, "write"))
    import pick
    ranked = pick.ranked()
    floor = float(os.environ.get("MIA_MIN_SCORE", "-1"))
    cands = [r for r in ranked if pick.score(r) >= floor][:max(12, n * 4)]
    log(f"選定: 未使用 {len(ranked)} 件 → スコア {floor} 以上の上位 {len(cands)} 件を AI で重複判定")
    if not cands: return []
    pub = "\n".join(f"- {a['date']} {a['title']}｜{a['src_title']}" for a in reversed(arts[-250:]))
    cand = "\n".join(f"{i}. [{r.get('published','')[:10]}] {r.get('title','')} — {(r.get('summary_ja') or '')[:160]}" for i, r in enumerate(cands, 1))
    res = ask_json(DEDUP.format(pub=pub, cand=cand))
    for k, why in (res.get("drop") or {}).items():
        try: log(f"  外す {k}. {cands[int(k) - 1].get('title','')[:40]} — {why}")
        except Exception: pass
    keep = [cands[i - 1] for i in res.get("keep", []) if isinstance(i, int) and 1 <= i <= len(cands)]
    return keep[:n]


# ---------- 5〜7 ----------
def write_one(row):
    sys.path.insert(0, os.path.join(REPO, "write")); sys.path.insert(0, os.path.join(REPO, "sns"))
    import article_ja, notion
    gen = article_ja.generate(row)
    slug, meta = article_ja.save(row, gen)
    pid, url = notion.create_article_page(meta)
    meta["notion_page"] = pid; meta["notion_url"] = url
    json.dump(meta, open(os.path.join(DATA, f"article_{slug}.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "used_urls.txt"), "a") as f: f.write(row["url"] + "\n")
    return slug


def step(cmd, timeout):
    log("実行:", " ".join(cmd))
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    print(r.stdout[-3000:], r.stderr[-1500:], flush=True)
    return r.returncode


if __name__ == "__main__":
    a = sys.argv[1:]
    n = int(a[a.index("--n") + 1]) if "--n" in a else int(os.environ.get("MIA_DAILY_N", "3"))
    env = setup()
    collect(env)
    arts = published()
    picks = choose(arts, n)
    for r in picks: log("  採用:", r.get("published", "")[:10], r.get("title", "")[:60])
    if "--dry" in a or not picks:
        log("記事にする候補なし" if not picks else "dry: ここで止める"); sys.exit(0)
    slugs = []
    for r in picks:
        try: slugs.append(write_one(r)); log("執筆:", slugs[-1])
        except Exception as e: log("!! 執筆失敗", r.get("title", "")[:40], str(e)[:200])
    if not slugs: sys.exit(1)
    rc = step(["python3", "write/publish_batch.py", "--batch", "20", "--workers", "3"], 3600)
    step(["python3", "sns/sns_texts.py"], 1800)
    log("完了:", len(slugs), "本", "publish rc", rc)
    sys.exit(rc)
