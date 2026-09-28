#!/usr/bin/env python3
"""汎用ヒーロー画像プール（フリー素材・Opus 検品済み）。記事固有の画像が引用でも素材でも取れなかった時の最後の受け皿。
キー = 酒の種類／話題。各キー 3 枚まで。data/hero_pool.json に保存。再実行で足りないキーだけ補充。
使い方: hero_pool_stock.py [key ...]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import stock
HOME = os.path.expanduser("~/mia-media"); OUT = os.path.join(HOME, "data", "hero_pool.json")
PER_KEY = 3

POOL = {
  "sake":    {"caption": "日本酒（イメージ）", "desc": "Japanese sake: cups, tokkuri, pouring or clear sake in a glass; Japan setting; no brand labels",
              "queries": ["sake cup pouring", "sake tokkuri ochoko", "japanese sake glass", "sake set wooden table", "masu sake cup", "sake ochoko closeup", "nihonshu pouring", "sake cup ceramic hands"]},
  "rice":    {"caption": "日本の田園（イメージ）", "desc": "Japanese rice paddies or rice ears, any season; clearly Japan; no people prominent",
              "queries": ["rice paddy japan", "rice ears closeup japan", "rice terraces japan morning", "rice field autumn japan"]},
  "shochu":  {"caption": "焼酎（イメージ）", "desc": "shochu or clear spirit on the rocks / with soda in a simple glass, Japanese izakaya or home setting; no labels",
              "queries": ["shochu on the rocks", "japanese highball glass", "clear spirit glass ice japan"]},
  "awamori": {"caption": "泡盛（イメージ）", "desc": "awamori or Okinawan spirit in a small glass or kame pot, Okinawa setting; no labels",
              "queries": ["awamori glass okinawa", "okinawa spirit glass", "shochu on the rocks", "okinawa pottery cup", "okinawa sea coast"]},
  "whisky":  {"caption": "ウイスキー（イメージ）", "desc": "whisky in a tumbler or nosing glass, amber, wooden bar or table; no bottle labels or logos",
              "queries": ["whisky glass neat", "whisky tasting glass dram", "whisky glass amber wooden bar"]},
  "gin":     {"caption": "ジン（イメージ）", "desc": "gin and tonic or clear spirit with botanicals in a glass; no bottle labels or logos",
              "queries": ["gin tonic glass botanicals", "gin glass juniper", "craft gin cocktail glass"]},
  "wine":    {"caption": "ワイン（イメージ）", "desc": "vineyard rows or a glass of wine; if a vineyard, plausible as Japan (hills, no Mediterranean cues); no labels",
              "queries": ["vineyard japan", "wine glass vineyard hills", "grapes vine closeup"]},
  "beer":    {"caption": "クラフトビール（イメージ）", "desc": "craft beer in a glass with foam, or brewery taproom taps; no brand logos or readable labels",
              "queries": ["craft beer glass foam", "beer taps taproom", "pale ale glass wooden bar"]},
  "export":  {"caption": "輸出のイメージ", "desc": "container port, cargo ship or shipping containers, or a wine/sake shop shelf abroad without readable brand labels",
              "queries": ["container port cargo ship", "shipping containers port sunset", "cargo ship harbour"]},
  "brewery": {"caption": "酒蔵（イメージ）", "desc": "exterior or interior of a traditional Japanese sake brewery: white plaster walls, dark wood, cedar ball (sugidama); no readable signage",
              "queries": ["sake brewery japan exterior", "sugidama cedar ball brewery", "old japanese storehouse kura"]},
  "market":  {"caption": "日本の酒類業界（イメージ）", "desc": "Japanese liquor shop shelves, izakaya counter or bar with bottles where no brand names are readable",
              "queries": ["izakaya counter japan night", "japanese bar counter bottles blur", "sake shop shelves japan", "izakaya lantern alley tokyo", "japanese bar interior warm light", "yokocho alley night"]},
}

def build(keys):
    pool = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for k in keys:
        spec = POOL[k]; have = pool.get(k, [])
        seen = {x["url"] for x in have}
        for q in spec["queries"]:
            if len(have) >= PER_KEY: break
            for c in stock.search(q, 4):
                if len(have) >= PER_KEY: break
                if c["url"] in seen: continue
                seen.add(c["url"])
                if stock.vet(c["url"], f"{spec['caption']} / {spec['desc']}"):
                    have.append({"url": c["url"], "credit": c["credit"], "caption": spec["caption"], "page": c.get("page")})
                    print(f"{k}: +1 ({len(have)}/{PER_KEY}) {c['credit']}", flush=True)
        pool[k] = have
        json.dump(pool, open(OUT, "w"), ensure_ascii=False, indent=1)
        print(f"{k}: {len(have)} images", flush=True)

if __name__ == "__main__":
    build(sys.argv[1:] or list(POOL))
