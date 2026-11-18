#!/usr/bin/env python3
"""写真の重複防止と「必ず 1 枚は付ける」選び方（2026-11-19 久保さん「サムネが無かったり全く一緒だったりしないように」）。

- used(): 公開済み記事（全言語 md の hero・本文画像）と IG カード台帳 sns/card_photos.json に出てくる写真の ID 一覧
- pick_unique(queries, desc, exclude): 検索語を順に試し、使用済みを除いたフリー素材から検品（stock.vet）に通った最初の 1 枚
- fallback_queries(text): 記事の文面から酒の種類を見て、汎用の検索語を足す（固有の検索語で取れなかったとき用）
画像は AI 生成しない（引用 → フリー素材）。フリー素材は Pexels・Unsplash・Openverse（stock.py）。"""
import glob, json, os, random, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import stock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTS = os.path.join(REPO, "site", "src", "content", "articles")
LEDGER = os.path.join(REPO, "sns", "card_photos.json")

_PAT = [r"pexels-photo-(\d+)", r"pexels\.com/photo/[^/]*?-?(\d+)/?$", r"images\.unsplash\.com/(photo-[\w-]+)",
        r"pixabay\.com/get/(\w+)", r"upload\.wikimedia\.org/.+/([^/?]+)$"]


def pid(url):
    """写真の同一性を判定する ID（サイズ・クエリ違いの URL を同じ写真として扱う）。"""
    u = (url or "").strip().strip('"')
    for p in _PAT:
        m = re.search(p, u)
        if m: return m.group(1)
    return re.sub(r"[?#].*", "", u)


def ledger():
    try: return json.load(open(LEDGER))
    except FileNotFoundError: return {}


def save_ledger(d):
    json.dump(d, open(LEDGER, "w"), ensure_ascii=False, indent=1, sort_keys=True)


def hero_index():
    """{写真 ID: [その写真をヒーローに使っている記事 slug（日付順）]}（en を正とする）"""
    idx = {}
    for f in sorted(glob.glob(os.path.join(ARTS, "en", "*.md"))):
        m = re.search(r'^hero:\s*"?([^"\n]+)"?\s*$', open(f).read().split("\n---", 1)[0], re.M)
        if m and m.group(1).strip() not in ("null", "''"):
            idx.setdefault(pid(m.group(1)), []).append(os.path.basename(f)[:-3])
    return idx


def used(extra=()):
    s = set()
    for f in glob.glob(os.path.join(ARTS, "*", "*.md")):
        t = open(f).read()
        for u in re.findall(r'^hero:\s*"?([^"\n]+)"?\s*$', t, re.M) + re.findall(r'<img src="([^"]+)"', t) + re.findall(r"\[\[image:([^|\]]+)", t):
            s.add(pid(u))
    for v in ledger().values(): s.add(pid(v.get("url")))
    for f in glob.glob(os.path.join(REPO, "data", "article_*.json")):   # 同じ実行で書いた未公開の原稿どうしも重複させない
        try: s.add(pid(json.load(open(f)).get("hero") or ""))
        except Exception: pass
    s.update(pid(u) for u in extra)
    s.discard("")
    return s


KINDS = [("awamori", ("awamori", "泡盛"), ["okinawa pottery jar", "okinawa clay pot", "okinawa village", "awamori"]),
         ("whisky", ("whisky", "whiskey", "distiller", "malt", "ウイスキー", "蒸溜", "蒸留"), ["whisky glass", "whisky barrels", "copper pot still", "whisky tasting", "oak cask"]),
         ("gin", ("gin ", "gin,", "gin.", "ジン"), ["gin tonic", "botanicals gin", "gin glass", "juniper berries", "cocktail bar"]),
         ("wine", ("wine", "winery", "vineyard", "grape", "ワイン", "ブドウ", "葡萄"), ["vineyard", "wine grapes", "wine glass", "wine cellar barrels", "grape harvest"]),
         ("beer", ("beer", "brewing co", "ipa", "ale", "stout", "ビール", "ブルワリー"), ["craft beer glass", "beer taps", "brewery tanks", "hops", "beer bottles"]),
         ("shochu", ("shochu", "焼酎"), ["sweet potato", "kagoshima", "japanese spirits glass", "distillery japan", "barley field"]),
         ("umeshu", ("umeshu", "plum wine", "梅酒"), ["japanese plum", "ume fruit", "plum blossom"]),
         ("sake", ("sake", "酒", "brewer", "junmai", "ginjo"), ["sake cup", "sake bottles", "sake brewery", "japanese sake", "sake barrels",
                                                               "rice paddy japan", "rice harvest", "tokkuri", "sake tasting", "izakaya", "japanese rice"])]
TOPIC = [(("export", "overseas", "輸出", "海外", "trade fair", "import"), ["shipping containers port", "cargo ship", "bottles shelf store"]),
         (("award", "gold", "platinum", "competition", "受賞", "medal"), ["tasting glasses", "medal", "wine tasting"]),
         (("rice", "farm", "paddy", "米", "田"), ["rice paddy", "rice field japan", "rice harvest"]),
         (("closure", "fire", "閉鎖", "廃業", "cease"), ["old japanese town", "empty street japan", "old wooden building japan"])]


def kind(title, text=""):
    """酒の種類。タイトルで決まればそれ、決まらなければ本文側で（日本酒の話がワイン樽に触れる、などの取り違えを避ける）。"""
    for t in ((title or "").lower(), (text or "").lower()):
        # いちばん先に出てくる種類の語で決める（"sake in a wine glass" は日本酒、"whisky aged in sake casks" はウイスキー）
        hits = sorted((min(t.find(w) for w in kw if w in t), i, name, q) for i, (name, kw, q) in enumerate(KINDS) if any(w in t for w in kw))
        if hits: return hits[0][2], hits[0][3]
    return KINDS[-1][0], KINDS[-1][2]


def fallback_queries(text, k=8, title=""):
    t = (text or "").lower(); top = []
    for kw, q in TOPIC:
        if any(w in t for w in kw): top += q[:2]
    qs = list(kind(title, text)[1]); random.shuffle(qs); random.shuffle(top)
    return (qs[:3] + top + qs[3:])[:k]   # 酒そのものの写真を先に、話題（輸出・受賞など）の写真を次に


def pick_unique(queries, desc, exclude=None, max_vet=6, generic=False, per_query=2):
    """queries を順に検索し、exclude（写真 ID）に無い候補を検品。通った最初の 1 枚（stock の候補 dict）を返す。
    1 つの検索語で検品するのは per_query 枚まで（同じ系統の写真ばかり落とし続けない）。"""
    ex = set(exclude if exclude is not None else used()); vetted = 0
    for q in [q for q in queries if q]:
        tried = 0
        for page in (1, 2):
            if tried >= per_query: break
            for c in stock.search(q, n=12, page=page):
                if pid(c["url"]) in ex or pid(c.get("page") or "") in ex: continue
                ex.add(pid(c["url"]))
                vetted += 1; tried += 1
                if stock.vet(c["url"], desc, generic=generic): stock.track(c); return c
                if vetted >= max_vet: return None
                if tried >= per_query: break
    return None
