#!/usr/bin/env python3
"""画像を差し込み直した確認待ち原稿を、1記事ずつ #biz-mia_media に再レビュー依頼する（2026-09-27）。
新しい投稿のスレッドを Notion の「Slackスレッド」に付け替えるので、返信（OK／見送り／直してほしい点）はそのスレッドで拾われる。
使い方: rereview_request.py [slug...]"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notion
from slack_post import post
HOME = os.path.expanduser("~/mia-media"); CH = os.environ.get("MIA_SLACK_CHANNEL", "C0C27TW71SN")

def counts(ja):
    body = ja.get("body_md", "")
    ai = len(re.findall(r"^\[\[image:[^\]]*AI生成[^\]]*\]\]", body, re.M))
    quoted = len(re.findall(r"^\[\[(?:image|youtube|x|instagram):", body, re.M)) - ai
    return quoted, ai

def main(slugs):
    pages = [p for p in notion.pending_pages(include_waiting=True) if notion.prop_select(p, "ステータス") == "確認待ち"]
    pages.sort(key=lambda p: notion.prop_text(p, "記事キー"))
    if slugs: pages = [p for p in pages if notion.prop_text(p, "記事キー") in slugs]
    for page in pages:
        slug = notion.prop_text(page, "記事キー"); mp = f"{HOME}/data/article_{slug}.json"
        if not os.path.exists(mp): continue
        meta = json.load(open(mp)); ja, r = meta["ja"], meta["row"]
        q, ai = counts(ja)
        hero = "引用" if meta.get("hero") and "AI生成" not in (meta.get("heroCredit") or "") else ("AI生成" if meta.get("hero") else "なし")
        url = meta.get("notion_url") or page.get("url")
        text = "\n".join([
            "🔁 *再レビュー依頼（画像を追加しました）*",
            f"*{ja['title']}*", ja.get("lead", ""), "",
            f"画像・動画: 引用 {q} 点 ／ AI生成 {ai} 点 ／ 冒頭画像: {hero}",
            f"元ネタ: <{r['url']}|{r['title'][:60]}>", "",
            f"👉 {url}",
            "このスレッドに返信: 「OK」→ 翻訳して公開 ／「見送り」→ 掲載しない ／ それ以外 → 直してほしい点として書き直し",
        ])
        res = post(CH, text)
        if res.get("ok"):
            notion.set_props(page["id"], slack=res["ts"])
            meta["last_feedback_ts"] = res["ts"]; json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
            print(f"posted {slug} ({q}/{ai}/{hero})")
        else:
            print(f"!! {slug}: {res}")
        time.sleep(1.2)

if __name__ == "__main__":
    main(sys.argv[1:])
