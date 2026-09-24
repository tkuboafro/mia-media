#!/usr/bin/env python3
"""ニュース1件 → 日本語の完成原稿（Notion でレビューする正本）。`claude -p`。
方針（久保さん 2026-09-16）: レビューは日本語で行う。外国語版は承認後に日本語から訳す。
出典は必ず明記し、原文の丸写しはしない（要約と自分の言葉で書く）。
画像（2026-09-24）: 見出しごとに1点。プレス画像・公式SNS・関連YouTube の引用を優先し、合うものが無い見出しだけ fal で生成（1記事最大2枚、AI生成と明記）。"""
import datetime as dt, json, os, re, subprocess, sys, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
from article import fetch_body, slugify, HOME
import kb, media as mediamod, genimg

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
{kbref}
{media}
{feedback}

【編集方針（最重要）】
- このメディアは「日本のお酒事情の最新情報」をヨーロッパの読者に伝えるもので、秋田県や自治体のプロモーションではない。
- 読者は日本に行かない前提。宿泊割引・観光キャンペーン・地域限定イベントのような「現地にいないと意味がない」情報は主題にしない。
  主題にするのは、海外でも意味がある話: 国際的な受賞、輸出・海外展開、造り手の物語と技術、新しい酒のスタイル、業界の変化、味わい方。
- 秋田はたまに触れる程度でよい。無理に秋田に結びつけない。
- 締めの段落は「ヨーロッパの読者がこの話をどう楽しめるか」（探し方・味わい方・注目点）にする。

【画像・動画（読んでいて楽しい記事にする。最重要の一つ）】
- 各「## 見出し」の直後の行に、その節の内容に合うメディアを1つ置く。書式は単独行で [[media:番号|日本語キャプション]]。
  番号は上の【利用できるメディア】の番号。同じ番号は2回使わない。ヒーローに使った画像は本文で使わない。
- 優先順位: 公式のプレス画像 → 公式のSNS投稿・公式YouTube → 内容が明確に一致する関連YouTube。銘柄名・蔵名が関係ない動画は使わない。
  "site" 種別（アカウントのトップページ等）は本文に置かない。
- 合うメディアが無い見出しには、代わりに単独行で [[gen:英語の画像プロンプト|日本語キャプション]] を置く（AIで生成する）。
  生成してよいのは一般的なもの（原料、酒器、グラス、飲み方、料理との組み合わせ、蔵や畑の一般的な情景）だけ。
  実在の銘柄・ボトル・ラベル・人物・特定の建物や場所は生成しない。gen は本文全体で最大2つ。引用で足りるなら0でよい。
- キャプションは写っているものを具体的に（例:「ISC 2026で金賞を受けた逢初」）。出典表記はシステムが付けるので書かない。

【書き方】
- 読者はオランダ・ドイツ・スペイン・英語圏のヨーロッパ人。翻訳されることを前提に、固有名詞は初出でフルネーム、日本語特有の言い回しは避け、EUの読者が知らない前提（秋田の場所、特定名称酒の等級、精米歩合の意味など）は本文で短く補う。
- 一次情報に無い事実・数字・引用を作らない。原文の文章をそのまま写さない（要約し、自分の言葉で書く）。
- 構成: リード1段落 → 見出し（##）2〜3本 → 締めにヨーロッパの読者向けの実用段落（どう楽しむか／どこに注目するか）。箇条書きは使わない。700〜1000字。
- 「MADE IN AKITA」の商品に明確に関係する場合のみ1回だけ触れてよい（売り込みはしない）。「飲酒は20歳/18歳から」などの注意書きは書かない（サイト側で付く）。
- 最後に「参考・出典」として、使った一次情報のURLを列挙する（本文中にURLは書かない）。

JSONだけを返す（コードフェンス不要）:
{{"title":"日本語の見出し（30字以内）","lead":"リード文（80字以内・1文）","body_md":"本文（Markdown。## 見出し、段落、見出し直後のメディア行）",
  "sources":[{{"name":"媒体名","title":"記事見出し","url":"URL"}}],
  "slug_en":"kebab-case-english-slug-max-60-chars","tags":["英語タグ3〜6個"],
  "hero_media":ヒーローに使う image の番号（整数。無ければ null）,"hero_caption":"ヒーロー画像のキャプション（日本語）",
  "hero_prompt":"hero_media が null の時だけ使う、記事に合う一般的な情景の英語プロンプト（実在の銘柄・ラベル・人物なし）"}}"""


MAX_GEN = 2

def place_media(gen, medias):
    """モデルの [[media:N|cap]] / [[gen:prompt|cap]] を実URLのショートコードへ。ヒーローも決める。"""
    def sub(mt):
        try: m = medias[int(mt.group(1)) - 1]
        except Exception: return ""
        cap = (mt.group(2) or "").strip("| ").strip()
        if m["type"] == "image": return f"[[image:{m['url']}|{cap}|{m.get('credit','')}]]"
        if m["type"] in ("youtube", "x", "instagram"): return f"[[{m['type']}:{m['url']}]]"
        return ""
    body = re.sub(r"\[\[media:(\d+)(\|[^\]]*)?\]\]", sub, gen["body_md"])
    n = 0
    def gsub(mt):
        nonlocal n
        prompt, _, cap = mt.group(1).partition("|")
        if n >= MAX_GEN: return ""
        url = genimg.try_generate(prompt.strip())
        if not url: return ""
        n += 1
        return f"[[image:{url}|{cap.strip()}|{genimg.CREDIT_JA}]]"
    body = re.sub(r"\[\[gen:([^\]]+)\]\]", gsub, body)
    body = re.sub(r"\[\[(youtube|image|x|instagram):(?!https?://)[^\]]*\]\]", "", body)
    gen["body_md"] = re.sub(r"\n{3,}", "\n\n", body)
    gen["media"] = medias
    gen["hero_image"] = None; gen["hero_credit"] = None
    try:
        hm = gen.get("hero_media")
        if hm is not None and medias[int(hm) - 1]["type"] == "image":
            m = medias[int(hm) - 1]
            gen["hero_image"] = m["url"]; gen["hero_credit"] = m.get("credit") or "画像提供: プレスリリースより"
    except Exception: pass
    if not gen["hero_image"] and gen.get("hero_prompt"):
        url = genimg.try_generate(gen["hero_prompt"])
        if url: gen["hero_image"] = url; gen["hero_credit"] = genimg.CREDIT_JA
    return gen

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
    place_media(gen, medias)
    # 出典は必ず元記事を含める
    have = {s.get("url") for s in gen.get("sources", [])}
    for x in [row] + list(extra):
        if x["url"] not in have:
            gen.setdefault("sources", []).append({"name": x.get("source", ""), "title": x["title"], "url": x["url"]})
    return gen

def save(row, gen, slug=None, date=None):
    date = date or dt.date.today()
    slug = slug or f"{date:%Y-%m-%d}-{slugify(gen.get('slug_en') or gen['title'])}"
    # 自社ストック（岩田さんの生成画像）を「自社素材」として流用するのは誤認を招くのでやめた。引用 or 生成 or なし。
    hero, alt, credit = gen.get("hero_image"), gen.get("hero_caption") or "", gen.get("hero_credit")
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
