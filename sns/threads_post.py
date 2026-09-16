#!/usr/bin/env python3
"""Threads（@thesakewire）へ投稿。Threads API（graph.threads.net）。
キー: ~/mia-media/secrets.env の THREADS_ACCESS_TOKEN（長期トークン 60日 → refresh() で延長）。
使い方: threads_post.py --whoami | --refresh | "本文"  """
import json, os, sys, time, urllib.request, urllib.parse
ENV = os.path.expanduser("~/mia-media/secrets.env"); API = "https://graph.threads.net/v1.0/"
def env():
    d = {}
    for l in open(ENV):
        if "=" in l and not l.startswith("#"): k, v = l.rstrip("\n").split("=", 1); d[k] = v.strip().strip('"')
    return d
def call(path, params, post=False):
    params["access_token"] = env()["THREADS_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode() if post else None
    url = API + path + ("" if post else "?" + urllib.parse.urlencode(params))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as ex:
        raise RuntimeError(f"Threads {ex.code}: {ex.read().decode()[:300]}")
def whoami(): return call("me", {"fields": "id,username,threads_profile_picture_url"})
def refresh():
    r = call("refresh_access_token", {"grant_type": "th_refresh_token"})
    s = open(ENV).read().replace(env()["THREADS_ACCESS_TOKEN"], r["access_token"]); open(ENV, "w").write(s)
    return r.get("expires_in")
def post_text(text, link=None):
    """テキスト投稿（link を付けるとリンクプレビュー）。500 字まで。"""
    uid = whoami()["id"]
    p = {"media_type": "TEXT", "text": text[:500]}
    if link: p["link_attachment"] = link
    c = call(f"{uid}/threads", p, post=True)
    time.sleep(3)
    r = call(f"{uid}/threads_publish", {"creation_id": c["id"]}, post=True)
    info = call(r["id"], {"fields": "permalink"})
    return r["id"], info.get("permalink")
def post_article(slug, meta, lang="en"):
    tr = (meta.get("translations") or {}).get(lang) or {}
    title = tr.get("title") or meta["ja"]["title"]; desc = tr.get("description") or ""
    url = f"https://sakewire.com/{lang}/{slug}/?utm_source=threads&utm_medium=social&utm_campaign={slug}"
    body = f"{title}\n\n{desc}"
    if len(body) > 470: body = body[:469].rstrip() + "…"
    return post_text(body, link=url)
if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "--whoami": print(whoami())
    elif a[0] == "--refresh": print("expires_in", refresh())
    else: print(post_text(a[0], a[1] if len(a) > 1 else None))
