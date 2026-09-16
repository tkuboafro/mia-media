#!/usr/bin/env python3
"""ニュース1件 → EN/NL/DE/ES の4本の記事（Markdown + frontmatter）。`claude -p` で生成、API キー不要。

翻訳ではなく各言語で書き起こす（EU の読者に向けた説明を足す）。原典は必ずリンクし、
原典に無い事実は書かない。"""
import datetime as dt, json, os, re, subprocess, sys, unicodedata

HOME = os.path.expanduser("~/mia-media")
SITE = os.path.join(HOME, "site")
LANGS = ["en", "nl", "de", "es"]
PREF = {"北海道": "Hokkaido", "青森": "Aomori", "岩手": "Iwate", "宮城": "Miyagi", "秋田": "Akita", "山形": "Yamagata", "福島": "Fukushima", "茨城": "Ibaraki", "栃木": "Tochigi", "群馬": "Gunma", "埼玉": "Saitama", "千葉": "Chiba", "東京": "Tokyo", "神奈川": "Kanagawa", "新潟": "Niigata", "富山": "Toyama", "石川": "Ishikawa", "福井": "Fukui", "山梨": "Yamanashi", "長野": "Nagano", "岐阜": "Gifu", "静岡": "Shizuoka", "愛知": "Aichi", "三重": "Mie", "滋賀": "Shiga", "京都": "Kyoto", "大阪": "Osaka", "兵庫": "Hyogo", "奈良": "Nara", "和歌山": "Wakayama", "鳥取": "Tottori", "島根": "Shimane", "岡山": "Okayama", "広島": "Hiroshima", "山口": "Yamaguchi", "徳島": "Tokushima", "香川": "Kagawa", "愛媛": "Ehime", "高知": "Kochi", "福岡": "Fukuoka", "佐賀": "Saga", "長崎": "Nagasaki", "熊本": "Kumamoto", "大分": "Oita", "宮崎": "Miyazaki", "鹿児島": "Kagoshima", "沖縄": "Okinawa", "全国": "Japan"}
def region_en(r):
    for k,v in PREF.items():
        if k in (r or ""): return v
    return "Japan" if r else ""

HERO_POOL = json.load(open(os.path.join(HOME, "write", "hero_pool.json"))) if os.path.exists(os.path.join(HOME, "write", "hero_pool.json")) else {}

PROMPT = """You are the editor of "The Sake Wire", an online magazine for readers in the EU (Netherlands, Germany, Spain and English-speaking Europe) about Japanese sake, wine, beer and spirits, run by a small importer in Amsterdam (shop.made-in-akita.com) that specialises in Akita prefecture.

Write ONE story in FOUR languages (en, nl, de, es) based ONLY on this Japanese source. Do not invent facts, quotes, numbers or names that are not in the source; where EU readers need background (what a term means, where Akita is, how sake grades work), add it as clearly general explanation. Each language version is written natively for that audience — not a translation — but they must tell the same story.

SOURCE (Japanese):
title: {title}
url: {url}
source: {source}
published: {published}
summary: {summary_ja}
region: {region}  category: {category}  akita: {akita}
why_eu: {why_eu}
{body}

Style: editorial, warm, concrete, 450–650 words per language. Structure: a strong lead paragraph, 2–3 short H2 sections (## ...), one practical closing paragraph for readers in Europe (how to taste / what to look for). No bullet lists. Do not mention that this is generated. Never write "Drink responsibly" in the body (the site adds it). If a shop product from Akita is clearly relevant you may mention "MADE IN AKITA" once, without hard selling.

Return ONLY a JSON object (no code fence):
{{"slug":"kebab-case-english-slug-max-60-chars",
  "hero_prompt":"English image-generation prompt for a photographic hero image that fits the story, no text, no logos, no people’s faces",
  "tags":["3-6 English tags"],
  "articles":{{
    "en":{{"title":"","description":"1 sentence, max 160 chars","body_md":"markdown body without the H1"}},
    "nl":{{"title":"","description":"","body_md":""}},
    "de":{{"title":"","description":"","body_md":""}},
    "es":{{"title":"","description":"","body_md":""}}
  }}}}"""

def fetch_body(url, limit=6000):
    """原典の本文を渡す（要約だけだと薄い）。取れなければ空。"""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MIA journal)"})
        raw = urllib.request.urlopen(req, timeout=20).read(600000)
    except Exception:
        return ""
    for enc in ("utf-8", "shift_jis", "euc-jp"):
        try: t = raw.decode(enc); break
        except Exception: t = ""
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t); t = re.sub(r"\s+", " ", t)
    # NUL や制御文字が混ざると subprocess が "embedded null byte" で落ちる（2026-09-16 05:30 の初回自動実行で発生）
    t = "".join(ch for ch in t if ch == "\n" or ord(ch) >= 32)
    return "SOURCE BODY (extracted text):\n" + t[:limit]

def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "story"

def pick_hero(row):
    """fal.ai が繋がるまでの暫定: 手持ちの蔵元/風景写真から地域・カテゴリで選ぶ。"""
    if not HERO_POOL: return None, None
    key = "akita" if row.get("akita") else "japan"
    cat = row.get("category") or ""
    for k in (f"{key}:{cat}", key, "japan"):
        if HERO_POOL.get(k):
            lst = HERO_POOL[k]
            i = sum(map(ord, row.get("url", ""))) % len(lst)
            return lst[i]["url"], lst[i].get("alt", "")
    return None, None

def generate(row, model="opus"):
    p = PROMPT.format(body=fetch_body(row["url"]), **{k: row.get(k) for k in ("title", "url", "source", "published", "summary_ja", "region", "category", "akita", "why_eu")})
    r = subprocess.run(["claude", "-p", p, "--output-format", "json", "--model", model, "--allowedTools", ""], capture_output=True, text=True, timeout=1200)
    try: raw = json.loads(r.stdout).get("result", "")
    except Exception: raw = r.stdout
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    i, j = raw.find("{"), raw.rfind("}")
    return json.loads(raw[i:j + 1])

def write_files(row, gen, date=None):
    date = date or dt.date.today()
    slug = slugify(gen.get("slug") or gen["articles"]["en"]["title"])
    slug = f"{date:%Y-%m-%d}-{slug}"
    hero, alt = pick_hero(row)
    paths = []
    for L in LANGS:
        a = gen["articles"][L]
        fm = {
            "title": a["title"], "description": a["description"][:200], "pubDate": date.isoformat(), "lang": L, "story": slug,
            "sourceUrl": row["url"], "sourceTitle": row["title"], "sourceName": row.get("source") or "",
            "region": row.get("region") or "", "regionEn": region_en(row.get("region")), "category": row.get("category") or "", "akita": bool(row.get("akita")),
            "tags": gen.get("tags", []),
        }
        if hero: fm["hero"] = hero; fm["heroAlt"] = alt or ""
        head = "---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items()) + "\n---\n\n"
        os.makedirs(os.path.join(SITE, "src", "content", "articles", L), exist_ok=True)
        path = os.path.join(SITE, "src", "content", "articles", L, f"{slug}.md")
        open(path, "w").write(head + a["body_md"].strip() + "\n")
        paths.append(path)
    meta = {"slug": slug, "hero_prompt": gen.get("hero_prompt"), "row": row, "date": date.isoformat(), "paths": paths}
    json.dump(meta, open(os.path.join(HOME, "data", f"article_{slug}.json"), "w"), ensure_ascii=False, indent=1)
    return slug, paths

if __name__ == "__main__":
    news = json.load(open(sys.argv[1]))
    row = news["rows"][int(sys.argv[2]) if len(sys.argv) > 2 else 0]
    gen = generate(row)
    slug, paths = write_files(row, gen)
    print(slug); [print(" ", p) for p in paths]
