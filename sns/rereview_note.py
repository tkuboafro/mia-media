#!/usr/bin/env python3
"""画像を差し替えた記事の Slack スレッドに補足を1件ずつ返す（再レビュー依頼の投稿は使い回す）。
使い方: rereview_note.py before.json   before = {slug: {"body":[urls], "hero":url}} 差し替え前の画像セット"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notion
from slack_post import post
HOME = os.path.expanduser("~/mia-media"); CH = os.environ.get("MIA_SLACK_CHANNEL", "C0C27TW71SN")

def kind(cred):
    if not cred: return "なし"
    if "AI生成" in cred: return "AI生成"
    if cred.startswith("写真: "): return "フリー素材"
    return "引用"

def main(before_path):
    before = json.load(open(before_path))
    pages = [p for p in notion.pending_pages(include_waiting=True) if notion.prop_select(p, "ステータス") == "確認待ち"]
    for p in pages:
        slug = notion.prop_text(p, "記事キー"); ts = notion.prop_text(p, "Slackスレッド").strip()
        meta = json.load(open(f"{HOME}/data/article_{slug}.json")); ja = meta["ja"]
        now = {"body": re.findall(r"^\[\[image:([^|\]]+)", ja["body_md"], re.M), "hero": meta.get("hero")}
        if not ts or before.get(slug) == now: print("unchanged", slug[:40]); continue
        creds = re.findall(r"^\[\[image:[^|\]]+\|[^|\]]*\|([^\]]*)\]\]", ja["body_md"], re.M)
        cnt = {}
        for c in creds: cnt[kind(c)] = cnt.get(kind(c), 0) + 1
        vids = len(re.findall(r"^\[\[(?:youtube|x|instagram):", ja["body_md"], re.M))
        parts = [f"{k} {v}点" for k, v in cnt.items()] + ([f"動画・投稿 {vids}点"] if vids else [])
        text = ("🖼️ 画像を差し替えました（引用 → フリー素材 → 生成 の順で選び直し、Opusで検品）\n"
                f"本文: {' ／ '.join(parts) or 'なし'} ／ 冒頭画像: {kind(meta.get('heroCredit'))}\n👉 {meta.get('notion_url')}")
        r = post(CH, text, ts); print("noted" if r.get("ok") else f"!! {r}", slug[:40])

if __name__ == "__main__":
    main(sys.argv[1])
