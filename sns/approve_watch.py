#!/usr/bin/env python3
"""#biz-mia_media のレビュー依頼メッセージに付いた ✅/❌ を見て PR をマージ／クローズする（launchd 15分毎）。
reactions:read スコープが無いので conversations.history のメッセージ本体に付く reactions を読む（実測で取れる）。"""
import json, os, subprocess, sys, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from slack_post import post, TOK
HOME = os.path.expanduser("~/mia-media")
APPROVER = os.environ.get("SLACK_APPROVER_ID", "U057NTPAT7X")   # 久保さん
SITE = "https://tkuboafro.github.io/mia-media"
OK = {"white_check_mark", "heavy_check_mark", "ballot_box_with_check", "+1"}
NG = {"x", "negative_squared_cross_mark", "-1"}

def message(channel, ts):
    q = urllib.parse.urlencode({"channel": channel, "latest": ts, "oldest": ts, "inclusive": "true", "limit": 1})
    req = urllib.request.Request(f"https://slack.com/api/conversations.history?{q}", headers={"Authorization": f"Bearer {TOK}"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return (d.get("messages") or [None])[0]

def verdict(msg):
    for r in (msg or {}).get("reactions", []):
        if APPROVER in r.get("users", []):
            if r["name"] in OK: return "ok"
            if r["name"] in NG: return "ng"
    return None

def gh(*a):
    return subprocess.run(["gh", *a], capture_output=True, text=True, cwd=HOME)

def main():
    p = f"{HOME}/data/pending_prs.json"
    if not os.path.exists(p): return
    pend = json.load(open(p)); keep = []
    for it in pend:
        v = verdict(message(it["channel"], it["ts"]))
        if v == "ok":
            r = gh("pr", "merge", it["pr"], "--squash", "--delete-branch")
            if r.returncode == 0:
                post(it["channel"], f"✅ 公開処理しました。数分で反映されます → {SITE}/en/{it['slug']}/ （nl/de/es も同時）", it["ts"])
            else:
                post(it["channel"], f"⚠️ マージに失敗: {r.stderr.strip()[:300]}", it["ts"]); keep.append(it)
        elif v == "ng":
            gh("pr", "close", it["pr"], "--delete-branch")
            post(it["channel"], "❌ 見送りにしました（PRをクローズ）。", it["ts"])
        else:
            keep.append(it)
    json.dump(keep, open(p, "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    os.environ["PATH"] = os.path.expanduser("~/.local/bin") + ":/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
    main()
