#!/usr/bin/env python3
"""記事を「文字だけ」にしないためのメディア収集（久保さん 2026-09-16: 画像・動画・公式の投稿を参照して読んでワクワクするものに）。
著作権の考え方: 転載ではなく「埋め込み・参照」。YouTube は公式の埋め込み、X/Instagram は公式の埋め込み、
画像は (a) 自社素材 (b) プレスリリース（PR TIMES 等）の報道用画像をクレジット付きで、に限る。
出力: [{"type": "youtube|x|instagram|image|site", "url":..., "title":..., "credit":..., "official": bool}]"""
import json, os, re, subprocess, sys, urllib.parse, urllib.request
CMD = os.path.expanduser("~/.local/share/danshiko/claude_browser/cmd.sh")
UA = {"User-Agent": "Mozilla/5.0 (The Sake Wire media check)"}

def get(url, limit=800000):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            raw = r.read(limit); ct = r.headers.get("content-type", "")
    except Exception:
        return "", ""
    for enc in ("utf-8", "shift_jis", "euc-jp"):
        try: return raw.decode(enc), ct
        except Exception: pass
    return "", ct

def head_ok(url):
    try:
        req = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as r: return r.status == 200
    except Exception:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r: return r.status == 200
        except Exception: return False

def from_source(url, source_name=""):
    """元記事ページから: og:image / 本文画像（PR TIMES）/ YouTube / X・Instagram の公式リンク"""
    html, _ = get(url)
    if not html: return []
    out, seen = [], set()
    def add(t, u, title="", credit="", official=False):
        key = u.split("?")[0] if u else ""
        if u and key not in seen:
            seen.add(key); out.append({"type": t, "url": u.replace("&amp;", "&"), "title": title, "credit": credit, "official": official})
    is_pr = "prtimes.jp" in url
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if m and is_pr:
        add("image", m.group(1), "", f"画像提供: {source_name or 'PR TIMES'}（プレスリリースより）", True)
    if is_pr:
        for u in re.findall(r'https://prcdn\.freetls\.fastly\.net/release_image/[^"\s]+?\.(?:jpg|jpeg|png)', html)[:6]:
            add("image", u.split("?")[0] + "?width=1200&height=900", "", f"画像提供: {source_name or 'PR TIMES'}（プレスリリースより）", True)
    for vid in re.findall(r'(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([A-Za-z0-9_-]{11})', html)[:3]:
        add("youtube", f"https://www.youtube.com/watch?v={vid}", "", "", True)
    for u in re.findall(r'https://(?:x|twitter)\.com/[A-Za-z0-9_]+/status/\d+', html)[:2]:
        add("x", u, "", "", True)
    for u in re.findall(r'https://www\.instagram\.com/(?:p|reel)/[A-Za-z0-9_-]+/?', html)[:2]:
        add("instagram", u, "", "", True)
    for u in re.findall(r'https://www\.instagram\.com/([A-Za-z0-9_.]+)/?"', html)[:1]:
        add("site", f"https://www.instagram.com/{u}/", f"Instagram @{u}", "", True)
    return out

def yt_tab():
    try:
        out = subprocess.run([CMD, json.dumps({"action": "tabs"})], capture_output=True, text=True, timeout=60).stdout
    except Exception: return None
    for line in out.splitlines():
        m = re.match(r"tab(\d+) .*  (\S+)$", line)
        if m and "youtube.com" in m.group(2): return int(m.group(1))
    subprocess.run([CMD, json.dumps({"action": "goto", "url": "https://www.youtube.com/", "wait": 3000})], capture_output=True, text=True, timeout=90)
    out = subprocess.run([CMD, json.dumps({"action": "tabs"})], capture_output=True, text=True, timeout=60).stdout
    ids = [int(x) for x in re.findall(r"^tab(\d+) ", out, re.M)]
    return max(ids) if ids else None

def youtube_search(query, k=3):
    """常駐ブラウザで YouTube 検索し、上位 k 本（動画ID・題名・チャンネル）を返す。API キー不要。"""
    q = urllib.parse.quote(query)
    js = ("(()=>{const out=[];const seen=new Set();for(const a of document.querySelectorAll('a#video-title')){"
          "const h=a.getAttribute('href')||'';const m=h.match(/v=([A-Za-z0-9_-]{11})/);if(!m||seen.has(m[1]))continue;seen.add(m[1]);"
          "const r=a.closest('ytd-video-renderer');const ch=r?((r.querySelector('ytd-channel-name a')||{}).textContent||'').trim():'';"
          "out.push({id:m[1],title:(a.getAttribute('title')||a.textContent||'').trim(),channel:ch});if(out.length>=%d)break;}return out;})()" % k)
    tab = yt_tab()
    if tab is None: return []
    try:
        subprocess.run([CMD, json.dumps({"action": "goto", "tab": tab, "url": f"https://www.youtube.com/results?search_query={q}", "wait": 4000})], capture_output=True, text=True, timeout=90)
        r = subprocess.run([CMD, json.dumps({"action": "eval", "tab": tab, "js": js}, ensure_ascii=False)], capture_output=True, text=True, timeout=90)
        return json.loads(r.stdout.strip())
    except Exception:
        return []

def yt_oembed(url):
    try:
        with urllib.request.urlopen("https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(url, safe=""), timeout=15) as r:
            d = json.load(r); return d.get("title", ""), d.get("author_name", "")
    except Exception: return None, None

def collect(row, brand_terms=()):
    """row: ニュース1件。brand_terms: 蔵元名・銘柄名（YouTube 検索と公式判定に使う）"""
    media = from_source(row["url"], row.get("source", ""))
    terms = [t for t in brand_terms if t] or []
    if terms:
        q = f"{terms[0]} 日本酒" if row.get("category") != "その他" else terms[0]
        for v in youtube_search(q, 3):
            url = f"https://www.youtube.com/watch?v={v['id']}"
            if any(m["url"] == url for m in media): continue
            official = any(t.lower() in (v.get("channel") or "").lower() for t in terms)
            media.append({"type": "youtube", "url": url, "title": v.get("title", ""), "credit": v.get("channel", ""), "official": official})
    # 実在確認（画像は HEAD、YouTube は oEmbed）
    ok = []
    for m in media:
        if m["type"] == "youtube":
            t, a = yt_oembed(m["url"])
            if t is None: continue
            m["title"] = m["title"] or t; m["credit"] = m["credit"] or a
        elif m["type"] == "image" and not head_ok(m["url"]): continue
        ok.append(m)
    return ok[:8]

def as_prompt(media):
    if not media: return "\n【利用できるメディア】なし（自社素材の写真のみ）\n"
    s = "\n【利用できるメディア（この中からだけ選ぶ。URLを変えない）】\n"
    for i, m in enumerate(media, 1):
        s += f"{i}. [{m['type']}{'・公式' if m.get('official') else ''}] {m['url']} {('— ' + m['title']) if m.get('title') else ''} {('（' + m['credit'] + '）') if m.get('credit') else ''}\n"
    return s

if __name__ == "__main__":
    row = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"url": "https://prtimes.jp/main/html/rd/p/000000022.000140111.html", "source": "PR TIMES", "category": "受賞"}
    print(json.dumps(collect(row, sys.argv[2:]), ensure_ascii=False, indent=1))
