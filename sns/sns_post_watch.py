#!/usr/bin/env python3
"""Notion「MIA SNS投稿管理」の「Xに投稿」「IGに投稿」チェックを見て Buffer から投稿する（launchd 5分毎）。2026-10-25 久保さん依頼。
- チェック＝その投稿の承認（投稿ごとの承認, 10/21 決定）。押すと次の巡回（最大5分）で即時投稿（Buffer shareNow）。
- 記事の行（チャネル=Journal）は、記事が公開済み（ステータス=投稿済み かつ URL が 200）になるまで「記事の承認待ち」で待つ。
- 本文は Notion の「X投稿文（Threads共用）」「IGキャプション」をそのまま使う（Notion で直した文が投稿される）。
- IG の画像: 記事 → make_card で作ったカード（sakewire.com/sns/<slug>-ig.png）。MIA の行 → 「メディアファイル」が無ければ「画像なし」。
- 状態: 記事の承認待ち → 予約済み（Buffer に送った）→ 投稿済み（投稿 URL 記入）／失敗。失敗のやり直しは状態を空にする。
使い方: sns_post_watch.py [--dry]  （--dry は Buffer の下書きに入れるだけで投稿しない）"""
import json, os, re, subprocess, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notion, buffer_client as bc, make_card, threads_post, sns_queue
HOME = os.path.expanduser("~/mia-media"); DRY = "--dry" in sys.argv
COL = {"x": ("Xに投稿", "X状態", "X投稿URL", "X投稿文（Threads共用）"), "threads": ("Threadsに投稿", "Threads状態", "Threads投稿URL", "X投稿文（Threads共用）"),
       "ig": ("IGに投稿", "IG状態", "IG投稿URL", "IGキャプション")}

def log(*a): print(time.strftime("%m-%d %H:%M"), *a, flush=True)
def ok_url(u):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).status == 200
    except Exception: return False
def setp(pid, **props): notion.api("PATCH", f"/pages/{pid}", {"properties": props})
def sel(v): return {"select": {"name": v} if v else None}
def rows():
    f = {"or": [{"property": c, "checkbox": {"equals": True}} for c in ("Xに投稿", "Threadsに投稿", "IGに投稿")]}
    body = {"filter": f, "page_size": 100}; out = []
    while True:
        r = notion.api("POST", f"/data_sources/{notion.DS}/query", body); out += r["results"]
        if not r.get("has_more"): return out
        body["start_cursor"] = r["next_cursor"]

def guard(ch, text):
    if not text.strip(): return "本文が空"
    if "18+" not in text: return "18+ 表記がない"
    if ch == "x" and len(re.sub(r"https?://\S+", "x" * 23, text)) > 280: return "280字を超えている"
    if ch == "threads" and len(text) > 500: return "500字を超えている"
    if ch == "ig" and len(text) > 2200: return "2200字を超えている"
    return None

def git_publish(path):
    """カード画像を GitHub Pages に載せる（コミットして push）。"""
    run = lambda *a: subprocess.run(a, cwd=HOME, capture_output=True, text=True)
    run("git", "pull", "-q", "--rebase", "--autostash"); run("git", "add", path)
    run("git", "-c", "user.name=MIA Journal bot", "-c", "user.email=tkubo@danshiko.com", "commit", "-q", "-m", f"sns: card {os.path.basename(path)}")
    for i in range(4):   # 記事の一括公開と push がぶつかることがある
        if run("git", "push", "-q").returncode == 0: return True
        time.sleep(15 * (i + 1)); run("git", "pull", "-q", "--rebase", "--autostash")
    return False

SENT = {}; POLLS = {"n": 0}
RETRY = f"{HOME}/data/sns/buffer_retry_at"
def buffer_blocked():
    try: return os.path.exists(RETRY) and time.time() < float(open(RETRY).read().strip() or 0)
    except Exception: return False
def _age(page):
    import datetime as _dt
    try: return time.time() - _dt.datetime.strptime(page.get("last_edited_time", ""), "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=_dt.timezone.utc).timestamp()
    except Exception: return 1e9

def handle(page):
    pid = page["id"]; slug = notion.prop_text(page, "記事キー").strip(); acct = notion.prop_select(page, "アカウント") or ""
    is_article = notion.prop_select(page, "チャネル") == "Journal"
    buf = notion.prop_text(page, "Buffer ID")
    for ch, (cb, stc, urlc, textc) in COL.items():
        if not page["properties"].get(cb, {}).get("checkbox"): continue
        if os.path.exists(f"{HOME}/data/sns/pause_{ch}"): continue   # 一時停止（X は Buffer 再接続待ち 2026-10-27）
        if ch in ("x", "ig") and buffer_blocked(): continue   # Buffer 250 req/24h の解除待ち
        st = notion.prop_select(page, stc)
        if st in ("投稿済み", "失敗"): continue
        if st == "予約済み":   # Buffer の結果を見に行く
            m = re.search(rf"{ch}:(\w+)", buf)
            if not m: continue
            if _age(page) < 300 or POLLS["n"] >= 3: continue   # 送信直後は見ない。確認は1巡回3件まで（Buffer 250 req/24h）
            POLLS["n"] += 1
            p = bc.get_post(m.group(1))
            if p["status"] == "sent": setp(pid, **{stc: sel("投稿済み"), urlc: {"url": p.get("externalLink") or None}}); log("sent", ch, slug or pid)
            elif p["status"] == "error": setp(pid, **{stc: sel("失敗")}); log("error", ch, slug or pid, (p.get("error") or {}).get("message"))
            else: setp(pid, **{"Buffer ID": {"rich_text": notion.rt(buf)}})   # 更新時刻を進めて、次の確認は5分後以降
            continue
        # まだ送っていない
        if is_article:
            meta = json.load(open(f"{HOME}/data/article_{slug}.json"))
            live = notion.prop_select(page, "ステータス") == "投稿済み" and ok_url(f"https://sakewire.com/en/{slug}/")
            if not live:
                if st != "記事の承認待ち": setp(pid, **{stc: sel("記事の承認待ち")})
                continue
            channel = {"x": "sakewire_x", "ig": "sakewire_ig", "threads": "threads"}[ch]
        else:
            if ch in ("x", "threads"): continue   # MIA は X・Threads を運用しない
            channel = "mia_ig" if "made_in_akita" in acct else "sakewire_ig"
        text = notion.prop_text(page, textc)
        bad = guard(ch, text)
        if bad: setp(pid, **{stc: sel("失敗")}); log("guard", ch, slug or pid, bad); continue
        if ch == "threads":   # Threads は API で直接（Buffer の無料枠は3チャネルまで）。即時に投稿済みになる
            if DRY: log("dry threads", slug); continue
            body = text.replace("utm_source=x", "utm_source=threads")
            link = re.search(r"https://sakewire\.com/\S+", body)
            tid, permalink = threads_post.post_text(body, link=link.group(0) if link else None)
            setp(pid, **{stc: sel("投稿済み"), urlc: {"url": permalink or None}}); log("sent threads", slug, tid)
            continue
        images = []
        if ch == "ig":
            if is_article:
                png, url = make_card.render(meta)
                if not ok_url(url):
                    if not DRY and not git_publish(png): log("card push failed", slug); continue
                    if not ok_url(url): log("card not live yet", slug); continue   # 次の巡回で再確認
                images = [url]
            else:
                files = (page["properties"].get("メディアファイル") or {}).get("files") or []
                images = [(f.get("external") or f.get("file") or {}).get("url") for f in files if f]
                images = [u for u in images if u]
                if not images:
                    if st != "画像なし": setp(pid, **{stc: sel("画像なし")})
                    continue
        if SENT.get(ch, 0) >= 3: continue   # 1巡回 1チャネル 3件まで（Buffer 100 req/15 min 対策）
        p = bc.create_post(channel, text, images=images, draft=DRY); SENT[ch] = SENT.get(ch, 0) + 1
        buf = (buf + f" {ch}:{p['id']}").strip()
        setp(pid, **{stc: sel("予約済み") if not DRY else None, "Buffer ID": {"rich_text": notion.rt(buf)}})
        log("queued" if not DRY else "draft", ch, channel, slug or pid, p["id"])

if __name__ == "__main__":
    if not DRY:
        try: sns_queue.tick(log=log)
        except Exception as e: log("!! queue", str(e)[:200])
    for page in rows():
        try: handle(page)
        except bc.RateLimited as e:
            open(RETRY, "w").write(str(time.time() + e.retry_after)); log(f"Buffer 429 — {e.retry_after}s 後まで Buffer を呼ばない"); break
        except Exception as e: log("!!", notion.prop_text(page, "記事キー") or page["id"], str(e)[:200])
