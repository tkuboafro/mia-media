#!/usr/bin/env python3
"""IG カードの写真を決める（2026-11-19 久保さん「サムネが無い・全く一緒、にならないように」）。

1. 記事のヒーローがフリー素材（写真: …）で、ほかの記事のヒーロー・カードに使われていない → それを使う
2. 台帳 sns/card_photos.json にこの記事の写真があれば → それを使う（作り直しても写真は変わらない）
3. 無ければ、使用済みを除いたフリー素材から 1 枚選んで検品し、台帳に足す
文字だけのカードは作らない（写真が取れなければ例外。カードが無い記事は IG に出ない）。
プレス画像（画像提供: …）・AI 画像は IG に使わない。"""
import os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "write"))
import photos


class NoPhoto(Exception): pass


def _who(credit):
    return "Photo: " + re.sub(r"<[^>]+>", "", credit.split(":", 1)[-1]).strip().replace("（", " (").replace("）", ")")


def from_pool(kind):
    """sns/photo_pool.json の kind から、どの記事・カードにも使われていない最初の 1 枚。"""
    import json
    try: pool = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "photo_pool.json")))
    except FileNotFoundError: return None
    used = photos.used()
    for c in pool.get(kind, []):
        if photos.pid(c["url"]) not in used:
            photos.stock.track(c); return c
    return None


def choose(meta, hero_idx=None, dry=False):
    """戻り値 (写真 URL, 'Photo: 撮影者 (提供元)')。"""
    slug = meta["slug"]; led = photos.ledger()
    if slug in led: return led[slug]["url"], led[slug]["credit"]
    hero, c = meta.get("hero"), meta.get("heroCredit") or ""
    idx = hero_idx if hero_idx is not None else photos.hero_index()
    if hero and c.startswith("写真") and "AI生成" not in c:
        h = photos.pid(hero)
        others = [s for s in idx.get(h, []) if s != slug]
        if not others and not any(photos.pid(v["url"]) == h for k, v in led.items() if k != slug):
            return hero, _who(c)
    tr = (meta.get("translations") or {}).get("en") or {}
    text = " ".join([tr.get("title") or "", tr.get("description") or "", meta.get("heroAlt") or "", " ".join(meta.get("tags") or [])])
    qs = [meta.get("hero_query")] + photos.fallback_queries(text, title=tr.get("title") or "")
    k = photos.kind(tr.get("title") or "", text)[0]
    desc = f"{k} — story: {tr.get('title') or ''}"
    if dry: return None, f"(dry) queries={qs[:4]}"
    p = from_pool(k)   # 検品済みの在庫（build_photo_pool.py）から未使用の 1 枚。無ければその場で探す
    if not p: p = photos.pick_unique(qs, desc, max_vet=8, generic=True)
    if not p: raise NoPhoto(f"{slug}: 使える写真が見つからない")
    credit = _who(p["credit"])
    led = photos.ledger(); led[slug] = {"url": p["url"], "credit": credit, "page": p.get("page")}; photos.save_ledger(led)
    return p["url"], credit
