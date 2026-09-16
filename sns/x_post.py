#!/usr/bin/env python3
"""X（@thesakewire）へ投稿。OAuth 1.0a User Context、キーは ~/mia-media/secrets.env。
使い方: x_post.py "本文"   → 投稿 ID を出力。`--whoami` で認証確認だけ。"""
import json, os, sys
from requests_oauthlib import OAuth1Session
ENV = os.path.expanduser("~/mia-media/secrets.env")
def env():
    d = {}
    for line in open(ENV):
        if "=" in line and not line.startswith("#"):
            k, v = line.rstrip("\n").split("=", 1); d[k] = v.strip().strip('"')
    return d
def session():
    e = env()
    return OAuth1Session(e["X_API_KEY"], e["X_API_SECRET"], e["X_ACCESS_TOKEN"], e["X_ACCESS_SECRET"])
def whoami():
    r = session().get("https://api.x.com/2/users/me"); return r.status_code, r.json()
def post(text):
    r = session().post("https://api.x.com/2/tweets", json={"text": text})
    if r.status_code not in (200, 201): raise RuntimeError(f"X {r.status_code}: {r.text[:300]}")
    return r.json()["data"]["id"]
def post_article(slug, meta, lang="en"):
    """公開した記事を X に1本投稿（EN）。本文は title + description + URL。280字に収める。"""
    tr = (meta.get("translations") or {}).get(lang) or {}
    title = tr.get("title") or meta["ja"]["title"]; desc = tr.get("description") or ""
    url = f"https://sakewire.com/{lang}/{slug}/?utm_source=x&utm_medium=social&utm_campaign={slug}"
    tags = " ".join("#" + t.replace(" ", "") for t in (meta["ja"].get("tags") or [])[:2])
    body = f"{title}\n\n{desc}"
    room = 280 - 23 - 2 - len(tags) - 2        # URL は 23 字換算
    if len(body) > room: body = body[:room - 1].rstrip() + "…"
    return post(f"{body}\n\n{url}\n{tags}".strip())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--whoami": print(whoami())
    else: print(post(sys.argv[1]))
