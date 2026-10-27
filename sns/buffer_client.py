#!/usr/bin/env python3
"""Buffer GraphQL API（https://api.buffer.com、Bearer）。キーは secrets.env の BUFFER_API_KEY、チャネル ID は buffer_channels.json。
使い方: buffer_client.py --channels"""
import json, os, sys, urllib.request
HOME = os.path.expanduser("~/mia-media")
CH = json.load(open(os.path.join(HOME, "sns", "buffer_channels.json")))["channels"]

def _key():
    for l in open(os.path.join(HOME, "secrets.env")):
        if l.startswith("BUFFER_API_KEY="): return l.split("=", 1)[1].strip()
    raise RuntimeError("BUFFER_API_KEY がない")

class RateLimited(Exception): pass

def gql(q, v=None):
    req = urllib.request.Request("https://api.buffer.com", data=json.dumps({"query": q, "variables": v or {}}).encode(),
                                 headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: d = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 429: raise RateLimited("Buffer 429")   # 100 req / 15 min。呼び出し側はその巡回を打ち切る
        raise
    if d.get("errors"): raise RuntimeError("Buffer: " + json.dumps(d["errors"], ensure_ascii=False)[:300])
    return d["data"]

POST_FIELDS = "id status externalLink error { message } dueAt sentAt channelService"
CREATE = """mutation($i: CreatePostInput!) { createPost(input: $i) {
  __typename ... on PostActionSuccess { post { %s } }
  ... on InvalidInputError { message } ... on UnexpectedError { message } ... on LimitReachedError { message }
  ... on NotFoundError { message } ... on UnauthorizedError { message } ... on RestProxyError { message } } }""" % POST_FIELDS

def create_post(channel, text, images=(), ig_type=None, draft=False, due_at=None):
    """channel: buffer_channels.json のキー（sakewire_x / sakewire_ig / mia_ig）。draft=True は Buffer の下書きに入れるだけ（投稿しない）。"""
    i = {"channelId": CH[channel]["id"], "text": text, "assets": [{"image": {"url": u}} for u in images],
         "schedulingType": "automatic", "mode": "customScheduled" if due_at else "shareNow"}
    if due_at: i["dueAt"] = due_at
    if draft: i["saveToDraft"] = True; i["mode"] = "addToQueue"
    if CH[channel]["service"] == "instagram": i["metadata"] = {"instagram": {"type": ig_type or "post", "shouldShareToFeed": True}}
    r = gql(CREATE, {"i": i})["createPost"]
    if r["__typename"] != "PostActionSuccess": raise RuntimeError(f"Buffer {r['__typename']}: {r.get('message')}")
    return r["post"]

def get_post(pid):
    return gql("query($i: PostInput!) { post(input: $i) { %s } }" % POST_FIELDS, {"i": {"id": pid}})["post"]

def delete_post(pid):
    return gql("mutation($i: DeletePostInput!) { deletePost(input: $i) { __typename } }", {"i": {"id": pid}})

if __name__ == "__main__":
    if "--channels" in sys.argv: print(json.dumps(CH, indent=1))
