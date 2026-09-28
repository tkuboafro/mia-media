#!/usr/bin/env python3
"""ヒーローや本文画像がゼロのままの確認待ち原稿に、汎用プール（フリー素材・検品済み）の画像を当てる最後の受け皿。
記事固有の引用・素材が取れなかった場合だけ。使用回数の少ない画像から順に使い、同じ写真が並ばないようにする。
使い方: sweep_images.py [--dry] [slug ...]"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sns"))
import notion
HOME = os.path.expanduser("~/mia-media"); POOL = os.path.join(HOME, "data", "hero_pool.json")
KEYS = [("awamori", ("泡盛",)), ("whisky", ("ウイスキー", "ウィスキー", "蒸溜所", "蒸留所", "モルト")), ("gin", ("ジン",)),
        ("wine", ("ワイン", "ワイナリー", "ブドウ", "葡萄")), ("beer", ("ビール", "ブルワリー", "ブリュー", "エール", "IPA", "スタウト")),
        ("shochu", ("焼酎",)),
        ("export", ("輸出", "海外", "ロンドン", "パリ", "EU", "欧州", "米国", "アジア", "シンガポール", "香港", "免税", "機内")),
        ("rice", ("酒米", "田んぼ", "稲", "農家", "米価", "概算金")),
        ("brewery", ("新蔵", "酒蔵", "蔵元", "杜氏", "醸造所", "復活", "再建", "新工場")),
        ("market", ("酒税", "統計", "業界", "制度", "GI")), ("sake", ())]

def key_for(meta):
    text = meta["ja"]["title"] + " " + (meta["row"].get("title") or "") + " " + (meta["row"].get("category") or "")
    for k, words in KEYS:
        if any(w in text for w in words): return k
    return "sake"

def main(argv):
    dry = "--dry" in argv; slugs = [a for a in argv if not a.startswith("--")]
    pool = json.load(open(POOL)) if os.path.exists(POOL) else {}
    if not any(pool.values()): print("pool is empty — run hero_pool_stock.py first"); return
    used = {}
    def take(k):
        cands = pool.get(k) or pool.get("sake") or []
        if not cands: return None
        c = min(cands, key=lambda x: used.get(x["url"], 0)); used[c["url"]] = used.get(c["url"], 0) + 1
        return c
    pages = [p for p in notion.pending_pages(include_waiting=True) if notion.prop_select(p, "ステータス") == "確認待ち"]
    n_hero = n_body = 0
    for p in pages:
        slug = notion.prop_text(p, "記事キー")
        if slugs and slug not in slugs: continue
        mp = f"{HOME}/data/article_{slug}.json"
        if not os.path.exists(mp): continue
        meta = json.load(open(mp)); ja = meta["ja"]; changed = False
        k = key_for(meta)
        if not meta.get("hero"):
            c = take(k)
            if c:
                meta["hero"], meta["heroAlt"], meta["heroCredit"] = c["url"], c["caption"], c["credit"]; ja["hero_caption"] = c["caption"]
                n_hero += 1; changed = True
        if not re.search(r"^\[\[(?:image|youtube|x|instagram):", ja["body_md"], re.M):
            c = take("rice" if k == "sake" else k)  # ヒーローと同じ写真が本文に並ばないように別キーから
            lines = ja["body_md"].splitlines()
            idx = next((i for i, l in enumerate(lines) if l.startswith("## ")), None)
            if c and idx is not None and c["url"] != meta.get("hero"):
                lines[idx + 1:idx + 1] = ["", f"[[image:{c['url']}|{c['caption']}|{c['credit']}]]", ""]
                ja["body_md"] = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip(); n_body += 1; changed = True
        if changed:
            print(f"{slug[:55]}: key={k} hero={'set' if meta.get('hero') else '-'}")
            if not dry:
                json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
                notion.replace_body(p["id"], meta)
    print(f"heroes set: {n_hero} / body images added: {n_body} {'(dry run)' if dry else ''}")

if __name__ == "__main__":
    main(sys.argv[1:])
