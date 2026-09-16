#!/usr/bin/env python3
"""Notion「MIA SNS投稿管理」DB で記事の制作進行を回す（REST API、トークン ~/.config/danshiko/notion_token）。

1ページ＝1記事（4言語の草稿を本文に持つ）。久保さんは Notion で本文を直し、ステータスを「承認 / 差戻し / 見送り」にする。
ページ本文の約束事（読み戻しに使う）:
  # EN — <title>       ← heading_1。言語コードと題名
  > <description>       ← quote。リード文
  ## ...  / 段落        ← 本文（heading_2 と paragraph だけ）
  ---                   ← divider で次の言語へ
"""
import json, os, re, sys, urllib.request

def _token():
    """社内共通の Notion 連携（旧名 myfans_weekly_bot → 改名予定 Otacon）のシークレット ~/.config/danshiko/notion_token。
    トークンは案件で分けない（2026-09-16 久保さん）。~/mia-media/secrets.env に NOTION_TOKEN があればそちらを優先。"""
    env = os.path.expanduser("~/mia-media/secrets.env")
    if os.path.exists(env):
        for line in open(env):
            if line.startswith("NOTION_TOKEN="): return line.split("=", 1)[1].strip().strip('"')
    p = os.path.expanduser("~/.config/danshiko/notion_token")
    return open(p).read().strip() if os.path.exists(p) else os.environ.get("NOTION_TOKEN", "")
TOK = _token()
DS = "fb94f323-ceec-4ef9-93bd-96e2fde80ab8"          # data source (collection) id
H = {"Authorization": f"Bearer {TOK}", "Notion-Version": "2025-09-03", "Content-Type": "application/json"}
LANGS = ["en", "nl", "de", "es"]
SITE = "https://sakewire.com"

def api(method, path, body=None):
    if not TOK: raise RuntimeError("NOTION_TOKEN missing — put it in ~/mia-media/secrets.env (integration 'MIA Journal')")
    req = urllib.request.Request("https://api.notion.com/v1" + path, data=json.dumps(body).encode() if body is not None else None, headers=H, method=method)
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"notion {method} {path}: {e.code} {e.read()[:300]}")

def rt(text):
    """rich_text は 2000 字/要素の上限。長い段落は分ける。"""
    return [{"type": "text", "text": {"content": text[i:i + 1900]}} for i in range(0, max(1, len(text)), 1900)]

def md_to_blocks(md):
    out = []
    for para in re.split(r"\n\s*\n", md.strip()):
        p = para.strip()
        if not p: continue
        if p.startswith("## "): out.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": rt(p[3:].strip())}})
        elif p.startswith("> "): out.append({"object": "block", "type": "quote", "quote": {"rich_text": rt(p[2:].strip())}})
        else: out.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": rt(" ".join(l.strip() for l in p.splitlines()))}})
    return out

def ja_blocks(meta):
    """日本語原稿ページの本文: 画像（自社素材＋クレジット） → # 見出し → > リード → 本文 → ## 参考・出典（箇条書きリンク）"""
    ja = meta["ja"]; blocks = []
    if meta.get("hero"):
        blocks.append({"object": "block", "type": "image", "image": {"type": "external", "external": {"url": meta["hero"]}, "caption": rt(meta.get("heroCredit") or "")}})
    blocks.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": rt(ja["title"])}})
    blocks.append({"object": "block", "type": "quote", "quote": {"rich_text": rt(ja["lead"])}})
    blocks += md_to_blocks(ja["body_md"])
    blocks.append({"object": "block", "type": "heading_2", "heading_2": {"rich_text": rt("参考・出典")}})
    for s_ in ja.get("sources", []):
        blocks.append({"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [
            {"type": "text", "text": {"content": f"{s_.get('name','')}「{s_.get('title','')}」", "link": {"url": s_["url"]}}}]}})
    blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": rt("本記事は上記の公開情報をもとに The Sake Wire 編集部が要約・執筆したものです。画像は自社素材を使用しています。")}})
    return blocks

def append_blocks(page_id, blocks):
    for i in range(0, len(blocks), 90):
        api("PATCH", f"/blocks/{page_id}/children", {"children": blocks[i:i + 90]})

def create_article_page(meta):
    slug, row, ja, date = meta["slug"], meta["row"], meta["ja"], meta["date"]
    props = {
        "投稿タイトル（管理用）": {"title": rt(f"Journal {date} {ja['title'][:40]}")},
        "チャネル": {"select": {"name": "Journal"}}, "種別": {"select": {"name": "記事"}}, "カテゴリ": {"select": {"name": "ニュース"}},
        "ステータス": {"select": {"name": "確認待ち"}},
        "投稿予定日": {"date": {"start": date}},
        "元記事": {"url": row["url"]}, "記事キー": {"rich_text": rt(slug)},
        "秋田": {"checkbox": bool(row.get("akita"))},
        "リンク先": {"url": f"{SITE}/en/{slug}/"},
        "UTM": {"rich_text": rt(f"utm_source=journal&utm_campaign={slug}")},
        "本文": {"rich_text": rt(ja["lead"])},
    }
    intro = [{"object": "block", "type": "callout", "callout": {"icon": {"emoji": "📰"}, "rich_text": rt(
        "レビュー方法: この日本語原稿が正本です。本文は直接直してOK（見出し・段落・出典）。ステータスを「承認」→ 英・蘭・独・西に翻訳してサイトに掲載（日本語版も掲載）。「差戻し」＋承認コメント → 書き直して再提出。「見送り」→ 不掲載。")}}]
    page = api("POST", "/pages", {"parent": {"type": "data_source_id", "data_source_id": DS}, "properties": props, "children": intro})
    append_blocks(page["id"], ja_blocks(meta))
    return page["id"], page["url"]

def replace_body(page_id, meta):
    """差戻し後の書き直し: 既存ブロックを消して入れ直す。"""
    r = api("GET", f"/blocks/{page_id}/children?page_size=100")
    for b in r["results"]:
        if b["type"] != "callout": api("DELETE", f"/blocks/{b['id']}")
    append_blocks(page_id, ja_blocks(meta))

def find_by_key(slug):
    r = api("POST", f"/data_sources/{DS}/query", {"filter": {"property": "記事キー", "rich_text": {"equals": slug}}, "page_size": 1})
    return (r.get("results") or [None])[0]

def pending_pages(include_waiting=False):
    sts = ("承認", "差戻し", "見送り") + (("確認待ち",) if include_waiting else ())
    r = api("POST", f"/data_sources/{DS}/query", {"filter": {"and": [{"property": "チャネル", "select": {"equals": "Journal"}},
            {"or": [{"property": "ステータス", "select": {"equals": s}} for s in sts]}]}, "page_size": 50})
    return r.get("results", [])

def prop_text(page, name):
    p = page["properties"].get(name) or {}
    t = p.get("rich_text") or p.get("title") or []
    return "".join(x.get("plain_text", "") for x in t)

def prop_select(page, name):
    return ((page["properties"].get(name) or {}).get("select") or {}).get("name")

def set_props(page_id, **kw):
    props = {}
    if "status" in kw: props["ステータス"] = {"select": {"name": kw["status"]}}
    if "post_url" in kw: props["投稿URL"] = {"url": kw["post_url"]}
    if "slack" in kw: props["Slackスレッド"] = {"rich_text": rt(kw["slack"])}
    if "comment" in kw: props["承認コメント"] = {"rich_text": rt(kw["comment"])}
    api("PATCH", f"/pages/{page_id}", {"properties": props})

def read_ja(page_id):
    """久保さんが直した後の日本語原稿を読み戻す → {title, lead, body_md, sources}"""
    blocks, cur = [], None
    while True:
        r = api("GET", f"/blocks/{page_id}/children?page_size=100" + (f"&start_cursor={cur}" if cur else ""))
        blocks += r["results"]
        if not r.get("has_more"): break
        cur = r["next_cursor"]
    def txt(b): return "".join(x.get("plain_text", "") for x in b[b["type"]].get("rich_text", []))
    out = {"title": "", "lead": "", "body": [], "sources": []}; in_src = False
    for b in blocks:
        t = b["type"]
        if t == "heading_1": out["title"] = txt(b).strip(); continue
        if t == "heading_2" and "出典" in txt(b): in_src = True; continue
        if in_src:
            if t == "bulleted_list_item":
                rts = b[t].get("rich_text", []); url = next((x["text"].get("link", {}) or {}).get("url") for x in rts if x.get("text", {}).get("link")) if any(x.get("text", {}).get("link") for x in rts) else None
                out["sources"].append({"name": "", "title": txt(b).strip(), "url": url or ""})
            continue
        if t == "quote" and not out["lead"]: out["lead"] = txt(b).strip()
        elif t == "heading_2": out["body"].append("## " + txt(b).strip())
        elif t == "paragraph" and txt(b).strip(): out["body"].append(txt(b).strip())
    out["body_md"] = "\n\n".join(out.pop("body"))
    return out

if __name__ == "__main__":
    print(json.dumps(api("GET", f"/data_sources/{DS}"), ensure_ascii=False)[:300])
