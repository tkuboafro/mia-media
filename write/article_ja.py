#!/usr/bin/env python3
"""ニュース1件 → 日本語の完成原稿（Notion でレビューする正本）。`claude -p`。
方針（久保さん 2026-09-16）: レビューは日本語で行う。外国語版は承認後に日本語から訳す。
出典は必ず明記し、原文の丸写しはしない（要約と自分の言葉で書く）。画像は自社素材のみ使い、出典記事の画像は使わない。"""
import datetime as dt, json, os, re, subprocess, sys, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
from article import fetch_body, pick_hero, slugify, HOME
import kb, media as mediamod

PROMPT = """あなたは「The Sake Wire」（アムステルダムの日本酒輸入業者が運営する、EU向け日本のお酒メディア）の編集者です。
以下の日本語の一次情報をもとに、**日本語で**1本の記事を書いてください。この日本語原稿が正本で、承認後に英・蘭・独・西へ翻訳して公開します。

【一次情報】{extra_sources}
見出し: {title}
URL: {url}
媒体: {source}
公開日: {published}
要約: {summary_ja}
地域: {region} / 分類: {category} / 秋田: {akita}
EU読者への切り口: {why_eu}
{body}
{feedback}

【編集方針（最重要）】
- このメディアは「日本のお酒事情の最新情報」をヨーロッパの読者に伝えるもので、秋田県や自治体のプロモーションではない。
- 読者は日本に行かない前提。宿泊割引・観光キャンペーン・地域限定イベントのような「現地にいないと意味がない」情報は主題にしない。
  主題にするのは、海外でも意味がある話: 国際的な受賞、輸出・海外展開、造り手の物語と技術、新しい酒のスタイル、業界の変化、味わい方。
- 秋田はたまに触れる程度でよい。無理に秋田に結びつけない。
- 締めの段落は「ヨーロッパの読者がこの話をどう楽しめるか」（探し方・味わい方・注目点）にする。

【書き方】
- 読者はオランダ・ドイツ・スペイン・英語圏のヨーロッパ人。翻訳されることを前提に、固有名詞は初出でフルネーム、日本語特有の言い回しは避け、EUの読者が知らない前提（秋田の場所、特定名称酒の等級、精米歩合の意味など）は本文で短く補う。
- 一次情報に無い事実・数字・引用を作らない。原文の文章をそのまま写さない（要約し、自分の言葉で書く）。
- 構成: リード1段落 → 見出し（##）2〜3本 → 締めにヨーロッパの読者向けの実用段落（どう楽しむか／どこに注目するか）。箇条書きは使わない。700〜1000字。
- 「MADE IN AKITA」の商品に明確に関係する場合のみ1回だけ触れてよい（売り込みはしない）。「飲酒は20歳/18歳から」などの注意書きは書かない（サイト側で付く）。
- 最後に「参考・出典」として、使った一次情報のURLを列挙する（本文中にURLは書かない）。

JSONだけを返す（コードフェンス不要）:
{{"title":"日本語の見出し（30字以内）","lead":"リード文（80字以内・1文）","body_md":"本文（Markdown。## 見出しと段落だけ）",
  "sources":[{{"name":"媒体名","title":"記事見出し","url":"URL"}}],
  "slug_en":"kebab-case-english-slug-max-60-chars","tags":["英語タグ3〜6個"],
  "hero_image":"ヒーローに使うプレスリリース画像のURL（リストの image から。無ければ null）","hero_caption":"ヒーロー画像のキャプション（日本語）",
  "hero_prompt":"記事に合う写真の英語プロンプト（文字・ロゴ・人物の顔なし）"}}"""

def generate(row, feedback=None, model="opus", extra=()):
    """extra: 同じ出来事を報じる別記事（row と同型）。本文の材料と出典に加える。"""
    fb = f"\n【前回の差戻しコメント（必ず反映する）】\n{feedback}\n" if feedback else ""
    xs = ""
    for x in extra:
        xs += f"\n（関連記事）{x.get('source','')}「{x['title']}」 {x['url']}\n" + fetch_body(x["url"], 3000)
    kbref = kb.as_prompt(kb.search(f"{row.get('title','')} {row.get('summary_ja','')}", "ja", 3))
    title = row.get("title") or ""
    terms = re.findall(r"「([^」]{2,20})」", title) + re.findall(r"([一-龠ぁ-んァ-ンA-Za-z]{2,12}(?:酒造店|酒造|醸造|蒸溜所|蒸留所|ワイナリー|ブルワリー|酒造場))", title)
    medias = mediamod.collect(row, terms[:3])
    p = PROMPT.format(body=fetch_body(row["url"]), feedback=fb, extra_sources=xs, kbref=kbref, media=mediamod.as_prompt(medias), **{k: row.get(k) for k in ("title", "url", "source", "published", "summary_ja", "region", "category", "akita", "why_eu")})
    r = subprocess.run(["claude", "-p", p, "--output-format", "json", "--model", model, "--allowedTools", ""], capture_output=True, text=True, timeout=1200)
    try: raw = json.loads(r.stdout).get("result", "")
    except Exception: raw = r.stdout
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    gen = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    # 本文末尾に「## 参考・出典」を書いてしまうことがある → 本文からは外す（sources で持つ）
    gen["body_md"] = re.split(r"\n##\s*参考[・･]?出典.*", gen["body_md"], flags=re.S)[0].rstrip()
    # リストに無いメディアURLは捨てる（捏造防止）
    allowed = {m["url"] for m in medias} | {m["url"].split("?")[0] for m in medias}
    def keep(mt):
        u = mt.group(2).split("|")[0].strip()
        return mt.group(0) if (u in allowed or u.split("?")[0] in allowed) else ""
    gen["body_md"] = re.sub(r"\[\[(youtube|image|x|instagram):([^\]]+)\]\]", keep, gen["body_md"])
    gen["media"] = medias
    hi = gen.get("hero_image")
    if hi and not (hi in allowed or hi.split("?")[0] in allowed): gen["hero_image"] = None
    # 出典は必ず元記事を含める
    have = {s.get("url") for s in gen.get("sources", [])}
    for x in [row] + list(extra):
        if x["url"] not in have:
            gen.setdefault("sources", []).append({"name": x.get("source", ""), "title": x["title"], "url": x["url"]})
    return gen

def save(row, gen, slug=None, date=None):
    date = date or dt.date.today()
    slug = slug or f"{date:%Y-%m-%d}-{slugify(gen.get('slug_en') or gen['title'])}"
    hero, alt = pick_hero(row); credit = "Photo: MADE IN AKITA（自社素材）" if hero else None
    if gen.get("hero_image"):
        m = next((m for m in gen.get("media", []) if m["url"] == gen["hero_image"] or m["url"].split("?")[0] == gen["hero_image"].split("?")[0]), None)
        hero, alt, credit = gen["hero_image"], gen.get("hero_caption") or "", (m or {}).get("credit") or "画像提供: プレスリリースより"
    meta = {"slug": slug, "date": date.isoformat(), "row": row, "ja": gen, "hero": hero, "heroAlt": alt, "heroCredit": credit}
    json.dump(meta, open(os.path.join(HOME, "data", f"article_{slug}.json"), "w"), ensure_ascii=False, indent=1)
    return slug, meta

if __name__ == "__main__":
    news = json.load(open(sys.argv[1]))
    row = news["rows"][int(sys.argv[2]) if len(sys.argv) > 2 else 0]
    extra = news.get("extra", [])
    gen = generate(row, extra=extra)
    slug, meta = save(row, gen); meta["extra"] = extra
    json.dump(meta, open(os.path.join(HOME, "data", f"article_{slug}.json"), "w"), ensure_ascii=False, indent=1)
    print(slug)
