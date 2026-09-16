#!/usr/bin/env python3
"""日本語原稿を Notion に作り、#biz-mia_media に Otacon としてレビュー依頼（日本語）を投稿する。
使い方: review_request.py <slug>"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notion
from slack_post import post
HOME = os.path.expanduser("~/mia-media"); CH = os.environ.get("MIA_SLACK_CHANNEL", "C0C27TW71SN")
def main(slug):
    mp = f"{HOME}/data/article_{slug}.json"; meta = json.load(open(mp)); r, ja = meta["row"], meta["ja"]
    pid, url = notion.create_article_page(meta)
    text = "\n".join([f"📰 *Journal 記事案（日本語原稿）* — Notion でレビューをお願いします", f"*{ja['title']}*", ja["lead"], "",
                      f"元ネタ: <{r['url']}|{r['title']}>（{r.get('source','')} / {r.get('published','')}）",
                      f"地域: {r.get('region','')} ／ 秋田: {'はい' if r.get('akita') else 'いいえ'}", "",
                      f"👉 {url}", "Notion のステータスを「承認」→ 英・蘭・独・西に翻訳して掲載（日本語版も）／「差戻し」＋承認コメント → 書き直し／「見送り」"])
    res = post(CH, text)
    if res.get("ok"): notion.set_props(pid, slack=res["ts"])
    meta["notion_page"] = pid; meta["notion_url"] = url; json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
    print(url)
if __name__ == "__main__":
    main(sys.argv[1])
