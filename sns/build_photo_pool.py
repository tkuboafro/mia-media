#!/usr/bin/env python3
"""IG カード用の汎用写真の在庫（酒の種類ごと・検品済み・未使用）を作る（2026-11-19）。
1 枚ずつ「探す→検品」だと遅く（約 6 分/枚）、受賞・輸出の話題語でワインやビールの写真ばかり拾って落ちていた。
→ 種類ごとの検索語で候補をまとめて取り、汎用写真の基準（stock.VET_GENERIC）で並列に検品して sns/photo_pool.json に貯める。
card_photo.choose はまずこの在庫から未使用の 1 枚を取る。
使い方: python3 sns/build_photo_pool.py [--workers 4] [kind=目標枚数 ...]   例: sake=160 beer=55"""
import json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "write"))
import photos, stock

POOL = os.path.join(HERE, "photo_pool.json")
QUERIES = {
    "sake": ["sake", "japanese sake", "sake cup", "sake bottle", "sake brewery", "sake barrel", "tokkuri", "ochoko", "masu cup", "sake tasting",
             "izakaya", "rice polishing", "japanese rice", "rice harvest japan", "sake brewery japan", "sake pouring", "japanese liquor", "nihonshu"],
    "beer": ["craft beer", "beer glass", "beer tap", "brewery tanks", "hops", "beer bottles", "pint of beer", "brewery", "craft brewery", "beer pouring"],
    "whisky": ["whisky glass", "whiskey glass", "whisky barrel", "pot still", "whisky distillery", "oak casks", "whiskey tasting", "japanese whisky"],
    "shochu": ["shochu", "japanese liquor glass", "sweet potato", "kagoshima", "distillery japan", "izakaya drinks", "barley grain", "japanese spirits"],
    "wine": ["vineyard", "wine grapes", "wine glass", "wine barrels", "grape harvest", "winery", "red wine", "white wine"],
    "gin": ["gin tonic", "gin glass", "juniper berries", "botanicals", "gin bottle", "cocktail glass gin"],
    "awamori": ["okinawa", "okinawa pottery", "awamori", "okinawa village", "clay jar"],
    "umeshu": ["umeshu", "japanese plum", "ume", "plum liqueur"],
}
DESC = {"sake": "Japanese sake", "beer": "craft beer (Japanese craft breweries)", "whisky": "whisky (Japanese distilleries)",
        "shochu": "Japanese shochu (sweet potato / barley / rice spirit)", "wine": "wine (Japanese wineries)", "gin": "craft gin (Japanese distilleries)",
        "awamori": "Okinawan awamori", "umeshu": "Japanese umeshu plum liqueur"}
lock = threading.Lock()


def load():
    try: return json.load(open(POOL))
    except FileNotFoundError: return {}


def main():
    a = [x for x in sys.argv[1:] if "=" in x]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    goal = {k: int(v) for k, v in (x.split("=") for x in a)} or {"sake": 160, "beer": 55, "whisky": 45, "shochu": 25, "wine": 20, "gin": 15, "awamori": 5, "umeshu": 3}
    pool = load(); ex = photos.used() | {photos.pid(p["url"]) for v in pool.values() for p in v}
    for kind, n in goal.items():
        have = len(pool.get(kind, []))
        if have >= n: continue
        cands = []
        for q in QUERIES[kind]:
            for page in (1, 2):
                for c in stock.search(q, n=30, page=page):
                    i = photos.pid(c["url"])
                    if i in ex: continue
                    ex.add(i); cands.append(c)
        print(kind, "候補", len(cands), "目標", n - have, flush=True)

        def one(c):
            with lock:
                if len(pool.get(kind, [])) >= n: return
            if stock.vet(c["url"], f"{DESC[kind]} — generic photo for any story about it", generic=True):
                with lock:
                    pool.setdefault(kind, []).append({"url": c["url"], "credit": c["credit"], "page": c.get("page"), "provider": c["provider"],
                                                      "dl": c.get("dl")})
                    json.dump(pool, open(POOL, "w"), ensure_ascii=False, indent=1)
        with ThreadPoolExecutor(workers) as tp: list(tp.map(one, cands))
        print(kind, "在庫", len(pool.get(kind, [])), flush=True)


if __name__ == "__main__":
    main()
