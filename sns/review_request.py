#!/usr/bin/env python3
"""記事PRのレビュー依頼を #biz-mia_media に Otacon として投稿し、data/pending_prs.json に控える。
使い方: review_request.py <slug> <pr_url>"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from slack_post import post
HOME = os.path.expanduser("~/mia-media")
CH = os.environ.get("MIA_SLACK_CHANNEL", "C0C27TW71SN")   # #biz-mia_media
SITE = "https://tkuboafro.github.io/mia-media"
def main(slug, pr_url):
    meta = json.load(open(f"{HOME}/data/article_{slug}.json")); r = meta["row"]
    lines = [f"📰 *Journal 本日の記事案* — レビューをお願いします", f"元記事: <{r['url']}|{r['title']}>（{r.get('source','')} / {r.get('published','')}）",
             f"地域: {r.get('region','')} ／ 分類: {r.get('category','')} ／ 秋田: {'はい' if r.get('akita') else 'いいえ'}", ""]
    for L in ("en", "nl", "de", "es"):
        t = open(f"{HOME}/site/src/content/articles/{L}/{slug}.md").read()
        ti = re.search(r'^title: "(.*)"', t, re.M).group(1); d = re.search(r'^description: "(.*)"', t, re.M).group(1)
        lines.append(f"*{L.upper()}* {ti}\n　{d}")
    lines += ["", f"本文: <{pr_url}/files|PR #{pr_url.rsplit('/',1)[1]} の Files changed>", "",
              "✅ を付ける → 4言語同時に公開（数分で反映）　　❌ を付ける → 見送り", "（このスレッドに「ここ直して: …」と書けば、次回生成の指示として記録します）"]
    res = post(CH, "\n".join(lines))
    if not res.get("ok"): print("slack error", res.get("error")); sys.exit(1)
    p = f"{HOME}/data/pending_prs.json"
    pend = json.load(open(p)) if os.path.exists(p) else []
    pend.append({"slug": slug, "pr": pr_url, "ts": res["ts"], "channel": CH})
    json.dump(pend, open(p, "w"), ensure_ascii=False, indent=1)
    print(res["ts"])
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
