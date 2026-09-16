#!/usr/bin/env python3
"""Otacon の Slack Bot トークン（~/.config/danshiko/slack_otacon_token）で #biz-mia_media に投稿する。
使い方: slack_post.py <channel_id> <text> [thread_ts]   → 投稿の ts を標準出力"""
import json, os, sys, urllib.request
TOK = open(os.path.expanduser("~/.config/danshiko/slack_otacon_token")).read().strip()
def post(channel, text, thread_ts=None):
    body = {"channel": channel, "text": text, "unfurl_links": False}
    if thread_ts: body["thread_ts"] = thread_ts
    req = urllib.request.Request("https://slack.com/api/chat.postMessage", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json; charset=utf-8"})
    return json.load(urllib.request.urlopen(req, timeout=30))
if __name__ == "__main__":
    r = post(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    if not r.get("ok"): print("ERR", r.get("error"), r.get("needed", ""), file=sys.stderr); sys.exit(1)
    print(r["ts"])
