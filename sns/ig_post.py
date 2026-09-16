#!/usr/bin/env python3
"""Instagram（@thesakewire）へ投稿。Instagram API with Instagram Login（graph.instagram.com）。
キー: ~/mia-media/secrets.env の META_ACCESS_TOKEN / IG_USER_ID。トークンは60日で切れる → refresh() を週1で回す。
使い方: ig_post.py --whoami | --refresh | <image_url> "<caption>" """
import json, os, sys, time, urllib.request, urllib.parse
ENV = os.path.expanduser("~/mia-media/secrets.env"); API = "https://graph.instagram.com/v21.0/"
def env():
    d = {}
    for l in open(ENV):
        if "=" in l and not l.startswith("#"): k, v = l.rstrip("\n").split("=", 1); d[k] = v.strip().strip('"')
    return d
def call(path, params, post=False):
    e = env(); params["access_token"] = e["META_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode() if post else None
    url = API + path + ("" if post else "?" + urllib.parse.urlencode(params))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as ex:
        raise RuntimeError(f"IG {ex.code}: {ex.read().decode()[:300]}")
def whoami(): return call("me", {"fields": "id,username,account_type,media_count"})
def refresh():
    """長期トークンを更新（有効期限60日 → 発行から24h以降なら更新可）。secrets.env を書き換える"""
    r = call("refresh_access_token", {"grant_type": "ig_refresh_token"})
    s = open(ENV).read().replace(env()["META_ACCESS_TOKEN"], r["access_token"]); open(ENV, "w").write(s)
    return r.get("expires_in")
def post_image(image_url, caption):
    uid = env()["IG_USER_ID"]
    c = call(f"{uid}/media", {"image_url": image_url, "caption": caption}, post=True)
    for _ in range(20):
        st = call(c["id"], {"fields": "status_code"})
        if st.get("status_code") == "FINISHED": break
        if st.get("status_code") == "ERROR": raise RuntimeError("container error " + json.dumps(st))
        time.sleep(3)
    r = call(f"{uid}/media_publish", {"creation_id": c["id"]}, post=True)
    info = call(r["id"], {"fields": "permalink"})
    return r["id"], info.get("permalink")
if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "--whoami": print(whoami())
    elif a[0] == "--refresh": print("expires_in", refresh())
    else: print(post_image(a[0], a[1]))
