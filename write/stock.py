#!/usr/bin/env python3
"""フリー素材の写真検索（引用できる素材が無い見出し用。生成より先に試す — 久保さん 2026-09-27「AI感が強いので基本は引用、無理ならフリー素材、それでも無ければ生成」）。
提供元: Openverse（鍵不要・CC BY/BY-SA/CC0/PDM のみ）, Pexels / Unsplash / Pixabay（secrets.env に鍵があれば）。
商用利用可・改変可のものだけ使い、クレジットは必ず付ける。"""
import json, os, re, sys, urllib.parse, urllib.request

HOME = os.path.expanduser("~/mia-media")
MIN_W = 1000
STOP = {"a", "an", "the", "of", "in", "on", "at", "with", "and", "or", "japanese", "japan", "photo", "image", "traditional"}

def _env(k):
    v = os.environ.get(k)
    if v: return v
    try:
        for line in open(os.path.join(HOME, "secrets.env")):
            if line.startswith(k + "="): return line.split("=", 1)[1].strip()
    except FileNotFoundError: pass
    return None

def _get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "sakewire/1.0 (editorial)", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)

def _toks(s): return {t for t in re.findall(r"[a-z]{3,}", (s or "").lower()) if t not in STOP}

def openverse(q, n):
    d = _get(f"https://api.openverse.org/v1/images/?{urllib.parse.urlencode({'q': q, 'license_type': 'commercial', 'page_size': n * 2, 'mature': 'false'})}")
    out = []
    for r in d.get("results", []):
        lic = (r.get("license") or "").lower()
        if "nd" in lic or "nc" in lic: continue  # 改変不可・非商用は使わない
        out.append({"url": r["url"], "width": r.get("width") or 0, "height": r.get("height") or 0, "title": r.get("title") or "",
                    "tags": " ".join(t.get("name", "") for t in (r.get("tags") or [])[:20]),
                    "credit": f"写真: {r.get('creator') or r.get('source')}（{r.get('source')}, CC {lic.upper()}）", "page": r.get("foreign_landing_url"), "provider": "openverse"})
    return out

def pexels(q, n):
    k = _env("PEXELS_KEY")
    if not k: return []
    d = _get(f"https://api.pexels.com/v1/search?{urllib.parse.urlencode({'query': q, 'per_page': n, 'orientation': 'landscape'})}", {"Authorization": k})
    return [{"url": p["src"]["large2x"], "width": p["width"], "height": p["height"], "title": p.get("alt") or "", "tags": "",
             "credit": f"写真: {p['photographer']}（Pexels）", "page": p["url"], "provider": "pexels"} for p in d.get("photos", [])]

def unsplash(q, n):
    k = _env("UNSPLASH_KEY")
    if not k: return []
    d = _get(f"https://api.unsplash.com/search/photos?{urllib.parse.urlencode({'query': q, 'per_page': n, 'orientation': 'landscape', 'content_filter': 'high'})}", {"Authorization": f"Client-ID {k}"})
    return [{"url": p["urls"]["regular"], "width": p["width"], "height": p["height"], "title": p.get("description") or p.get("alt_description") or "",
             "tags": " ".join(t.get("title", "") for t in p.get("tags", [])), "credit": f"写真: {p['user']['name']}（Unsplash）", "page": p["links"]["html"], "provider": "unsplash"} for p in d.get("results", [])]

def pixabay(q, n):
    k = _env("PIXABAY_KEY")
    if not k: return []
    d = _get(f"https://pixabay.com/api/?{urllib.parse.urlencode({'key': k, 'q': q, 'per_page': max(3, n), 'image_type': 'photo', 'orientation': 'horizontal', 'safesearch': 'true'})}")
    return [{"url": p["largeImageURL"], "width": p["imageWidth"], "height": p["imageHeight"], "title": "", "tags": p.get("tags", ""),
             "credit": f"写真: {p['user']}（Pixabay）", "page": p["pageURL"], "provider": "pixabay"} for p in d.get("hits", [])]

def search(q, n=6):
    cands = []
    for fn in (pexels, unsplash, pixabay, openverse):
        try: cands += fn(q, n)
        except Exception as e: print(f"[stock] {fn.__name__}: {e}", file=sys.stderr)
    qt = _toks(q)
    scored = []
    for c in cands:
        if c["width"] < MIN_W: continue
        hit = len(qt & _toks(f"{c['title']} {c['tags']}"))
        need = 2 if c["provider"] == "openverse" else 1  # Openverse は玉石混交なので厳しめ
        if hit < need: continue
        pri = {"pexels": 0, "unsplash": 0, "pixabay": 1, "openverse": 2}[c["provider"]]
        scored.append((pri, -hit, -c["width"], c))
    scored.sort(key=lambda x: x[:3])
    return [x[3] for x in scored[:n]]

VET_PROMPT = ('Read the image file {path} and judge it as an editorial illustration for a Japanese drinks news article, intended to show: "{desc}". '
              'Answer ONLY JSON: {{"ok": true|false, "reason": "<10 words"}}. ok=false if the scene clearly is not Japan (when the subject is place-specific), '
              'or it shows readable text, brand labels or logos, or a recognizable face is prominent, or the subject does not match, or it looks obviously fake/AI-artifacted.')

def vet(url, desc):
    """Haiku に画像を見せて可否を判定（数秒・少トークン）。判定不能なら False（安全側）。"""
    import subprocess, tempfile
    try:
        fd, path = tempfile.mkstemp(suffix=".jpg"); os.close(fd)
        urllib.request.urlretrieve(url, path)
        r = subprocess.run(["claude", "-p", VET_PROMPT.format(path=path, desc=desc), "--model", "haiku", "--allowedTools", "Read", "--output-format", "json"],
                           capture_output=True, text=True, timeout=120)
        raw = json.loads(r.stdout).get("result", ""); j = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        if not j.get("ok"): print(f"[vet] NG {url[:60]}: {j.get('reason')}", file=sys.stderr)
        return bool(j.get("ok"))
    except Exception as e:
        print(f"[vet] error: {e}", file=sys.stderr); return False
    finally:
        try: os.remove(path)
        except Exception: pass

def pick(q, desc=None, n=3):
    """検索語で探し、上位 n 件を順に検品して最初に通ったものを返す。desc: 何を見せたいか（日本語可）。"""
    for c in search(q, n):
        if desc is None or vet(c["url"], desc): return c
    return None

if __name__ == "__main__":
    for c in search(" ".join(sys.argv[1:]) or "sake brewery", 5):
        print(c["provider"], c["width"], c["title"][:40], "|", c["credit"], "|", c["url"][:80])
