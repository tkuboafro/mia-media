#!/usr/bin/env python3
"""確認待ちの原稿に、本文は変えずに画像・動画だけ差し込む（2026-09-24、素材がプロンプトに渡っていなかった不具合の後始末）。
使い方: retrofit_media.py            … 確認待ち全部
        retrofit_media.py <slug>...  … 指定だけ
        retrofit_media.py --fill     … 前回の配置を再利用して [[gen:]] だけ作り直す（fal に入金した後に使う。モデル呼び出しなし）"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sns"))
import article_ja, notion, media as mediamod
from article import HOME

PROMPT = """次の日本語記事の本文に、画像・動画を差し込む位置を決めてください。**本文の文章は一字も変えないこと。** 行を足すだけです。

【ルール】
- 各「## 見出し」の直後に1行、その節に合うメディアを置く。書式は単独行で [[media:番号|日本語キャプション]]。同じ番号は2回使わない。
- 優先順位: 公式のプレス画像 → 公式のSNS投稿・公式YouTube → 内容が明確に一致する関連YouTube。"site" 種別は置かない。
- 合うメディアが無い見出しには単独行で [[gen:英語の画像プロンプト|日本語キャプション]] を置く（AI生成）。本文全体で最大2つ。
  生成してよいのは一般的なもの（原料、酒器、グラス、飲み方、料理、蔵や畑の一般的な情景）だけ。実在の銘柄・ボトル・ラベル・人物・特定の建物は不可。
- ヒーロー（記事冒頭の大きな画像）に使う image の番号を hero_media に。本文で使った番号はヒーローに使わない（逆も同じ）。
  使える image が無ければ hero_media は null にして、hero_prompt に一般的な情景の英語プロンプトを書く。
- キャプションは写っているものを具体的に。出典はシステムが付けるので書かない。

【記事】
{body}

{media}

JSONだけを返す: {{"body_md":"差し込み済みの本文","hero_media":番号またはnull,"hero_caption":"日本語","hero_prompt":"英語またはnull"}}"""

MEDIA_LINE = re.compile(r"^\[\[(?:media|gen|image|youtube|x|instagram):[^\]]*\]\]\s*$", re.M)

def text_only(md):
    return re.sub(r"\s+", "", MEDIA_LINE.sub("", md))

def transplant(base, placed_md):
    """モデル出力から「どの見出しの直後に何を置いたか」だけを取り出し、元の本文に差し込む（本文は一字も変えない）。"""
    picks, cur = {}, None
    for line in placed_md.splitlines():
        h = re.match(r"^##\s*(.+?)\s*$", line)
        if h: cur = re.sub(r"\s+", "", h.group(1)); continue
        if cur is not None and MEDIA_LINE.match(line.strip()) and cur not in picks: picks[cur] = line.strip()
    out = []
    for line in base.splitlines():
        out.append(line)
        h = re.match(r"^##\s*(.+?)\s*$", line)
        if h:
            key = re.sub(r"\s+", "", h.group(1))
            tag = picks.get(key) or next((v for k, v in picks.items() if k[:8] == key[:8]), None)
            if tag: out.append(tag)
    return "\n".join(out)

def place_with_model(body, medias):
    p = PROMPT.format(body=body, media=mediamod.as_prompt(medias))
    r = subprocess.run(["claude", "-p", p, "--output-format", "json", "--model", "sonnet", "--allowedTools", ""], capture_output=True, text=True, timeout=600)
    try: raw = json.loads(r.stdout).get("result", "")
    except Exception: raw = r.stdout
    return json.loads(raw[raw.find("{"):raw.rfind("}") + 1])

def retrofit(page, fill=False):
    slug = notion.prop_text(page, "記事キー")
    mp = os.path.join(HOME, "data", f"article_{slug}.json")
    if not os.path.exists(mp): print(f"skip {slug}: no meta"); return
    meta = json.load(open(mp)); ja = meta["ja"]
    now = notion.read_ja(page["id"])  # Notion 上の手直しを優先
    base = MEDIA_LINE.sub("", now.get("body_md") or ja["body_md"]).strip()
    base = re.sub(r"\n参考・出典[\s\S]*$", "", base).strip()
    for k in ("title", "lead"):
        if now.get(k): ja[k] = now[k]
    if fill and ja.get("body_placed_raw"):
        placed = {"body_md": transplant(base, ja["body_placed_raw"]), **{k: ja.get(k) for k in ("hero_media", "hero_caption", "hero_prompt")}}
        medias = ja.get("media", [])
    else:
        medias = mediamod.collect(meta["row"], article_ja.brand_terms(meta["row"]))
        placed = place_with_model(base, medias)
        placed["body_md"] = transplant(base, placed["body_md"])  # モデルの本文は使わず、配置だけ元の本文へ移植する
    ja["body_placed_raw"] = placed["body_md"]
    ja.update({"body_md": placed["body_md"], "hero_media": placed.get("hero_media"), "hero_caption": placed.get("hero_caption") or "",
               "hero_prompt": placed.get("hero_prompt")})
    article_ja.place_media(ja, medias)
    meta["hero"], meta["heroAlt"], meta["heroCredit"] = ja.get("hero_image"), ja.get("hero_caption") or "", ja.get("hero_credit")
    json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
    notion.replace_body(page["id"], meta)
    n_img = len(re.findall(r"^\[\[(?:image|youtube|x|instagram):", ja["body_md"], re.M))
    n_gen_wanted = len(re.findall(r"\[\[gen:", ja["body_placed_raw"]))
    print(f"{slug}: 本文メディア {n_img} / 生成待ち {n_gen_wanted} / ヒーロー {'あり' if meta['hero'] else 'なし'}")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]; fill = "--fill" in sys.argv
    pages = [p for p in notion.pending_pages(include_waiting=True) if notion.prop_select(p, "ステータス") == "確認待ち"]
    if args: pages = [p for p in pages if notion.prop_text(p, "記事キー") in args]
    for p in pages:
        try: retrofit(p, fill)
        except Exception as e: print(f"!! {notion.prop_text(p, '記事キー')}: {e}")
