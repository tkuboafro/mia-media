#!/usr/bin/env python3
"""Notion の記事ページのステータスを見て動く（launchd 15分毎）。
  承認   → 久保さんの手直し済み日本語を読み戻し → 翻訳 → サイト公開 → 投稿済み＋投稿URL、Slack スレッドに報告
  差戻し → 承認コメントを反映して日本語を書き直し → ページ本文を差し替え → 確認待ち、Slack スレッドに報告
  見送り → 記録して終了"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "write"))
import notion
from slack_post import post
HOME = os.path.expanduser("~/mia-media"); PUB = "https://tkuboafro.github.io/mia-media"
CH = os.environ.get("MIA_SLACK_CHANNEL", "C0C27TW71SN")

def slack_ts(page):
    return notion.prop_text(page, "Slackスレッド").strip() or None

import urllib.request, urllib.parse
from slack_post import TOK
APPROVER = os.environ.get("SLACK_APPROVER_ID", "U057NTPAT7X")   # 久保さん
OK_WORDS = ("承認", "OK", "ok", "公開して", "これでいい", "問題ない", "GO", "go")
NG_WORDS = ("見送り", "ボツ", "ぼつ", "NG", "掲載しない", "やめ")

def thread_feedback(ts, after_ts):
    """レビュー依頼スレッドの、久保さんの新しい返信を返す（after_ts より後）。"""
    q = urllib.parse.urlencode({"channel": CH, "ts": ts, "limit": 50})
    req = urllib.request.Request(f"https://slack.com/api/conversations.replies?{q}", headers={"Authorization": f"Bearer {TOK}"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    msgs = [m for m in d.get("messages", []) if m.get("user") == APPROVER and m.get("ts") != ts and float(m.get("ts", 0)) > float(after_ts or 0)]
    return msgs

def classify(text):
    t = text.strip()
    if len(t) <= 12 and any(w in t for w in OK_WORDS): return "ok"
    if len(t) <= 12 and any(w in t for w in NG_WORDS): return "ng"
    return "feedback"

def main():
    try:
        pages = notion.pending_pages(include_waiting=True)
    except Exception as e:
        # 統合（myfans_weekly_bot）が DB に接続されていないと 404。久保さんが Notion 側で「接続」を足すまで待つ
        print("notion not reachable:", str(e)[:200]); return
    for page in pages:
        slug = notion.prop_text(page, "記事キー").strip(); st = notion.prop_select(page, "ステータス"); pid = page["id"]
        mp = f"{HOME}/data/article_{slug}.json"
        if not slug or not os.path.exists(mp): print("skip (no meta)", slug, st); continue
        meta = json.load(open(mp)); ts = slack_ts(page)
        # Slack スレッドの返信 → 承認 / 見送り / 差戻しコメント として扱う（Notion を開かなくても回るように）
        if st == "確認待ち" and ts:
            new = thread_feedback(ts, meta.get("last_feedback_ts"))
            if new:
                meta["last_feedback_ts"] = new[-1]["ts"]; json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
                kinds = [classify(m.get("text", "")) for m in new]
                if "feedback" in kinds:
                    comment = "\n".join(m.get("text", "") for m in new if classify(m.get("text", "")) == "feedback")
                    notion.set_props(pid, status="差戻し", comment=comment); st = "差戻し"
                elif "ng" in kinds: notion.set_props(pid, status="見送り"); st = "見送り"
                elif "ok" in kinds: notion.set_props(pid, status="承認"); st = "承認"
                page = notion.api("GET", f"/pages/{pid}")
        if st == "承認":
            ja = notion.read_ja(pid)
            if ja["title"] and ja["body_md"]:
                meta["ja"].update({"title": ja["title"], "lead": ja["lead"] or meta["ja"]["lead"], "body_md": ja["body_md"]})
                if ja["sources"]: meta["ja"]["sources"] = [s for s in ja["sources"] if s.get("url")] or meta["ja"]["sources"]
                json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
            notion.set_props(pid, status="制作中")   # 二重処理防止
            r = subprocess.run(["/usr/bin/python3", f"{HOME}/publish.py", slug], capture_output=True, text=True)
            if r.returncode == 0:
                url = r.stdout.strip().splitlines()[-1]
                notion.set_props(pid, status="投稿済み", post_url=url)
                post(CH, f"✅ 公開しました（数分で反映）\n日本語: {url}\nEN: {PUB}/en/{slug}/  NL: {PUB}/nl/{slug}/  DE: {PUB}/de/{slug}/  ES: {PUB}/es/{slug}/", ts)
            else:
                notion.set_props(pid, status="承認")
                post(CH, f"⚠️ 公開処理に失敗しました（再試行します）: {(r.stderr or r.stdout)[-300:]}", ts)
        elif st == "差戻し":
            comment = notion.prop_text(page, "承認コメント").strip() or "（コメントなし）"
            from article_ja import generate
            notion.set_props(pid, status="制作中")
            gen = generate(meta["row"], feedback=comment)
            meta["ja"] = gen; meta.setdefault("feedback_log", []).append(comment)
            json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
            notion.replace_body(pid, meta)
            notion.set_props(pid, status="確認待ち")
            post(CH, f"🔁 差戻しコメント「{comment[:80]}」を反映して書き直しました。Notion で再確認をお願いします → {page['url']}", ts)
        elif st == "見送り":
            if not meta.get("skipped"):
                meta["skipped"] = True; json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
                post(CH, "❌ 見送りを記録しました。", ts)

if __name__ == "__main__":
    os.environ["PATH"] = os.path.expanduser("~/.local/bin") + ":/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
    main()
