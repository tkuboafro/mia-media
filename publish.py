#!/usr/bin/env python3
"""承認済み日本語原稿 → 翻訳 → md 5言語（ja/en/nl/de/es）→ main に commit/push（GitHub Pages が配信）。
使い方: publish.py <slug>   （data/article_<slug>.json の ja を最終稿として使う）"""
import datetime as dt, json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "write"))
from translate import translate
HOME = os.path.dirname(os.path.abspath(__file__)); SITE = os.path.join(HOME, "site")
PUB = "https://sakewire.com"

def fm_line(k, v): return f"{k}: {json.dumps(v, ensure_ascii=False)}"

import re, html as _html
def render_media(md):
    """[[youtube:...]] などを埋め込み HTML に。YouTube は youtube-nocookie、X/Instagram は公式ウィジェット。"""
    need = set()
    def rep(m):
        kind, rest = m.group(1), m.group(2).split("|"); url = _html.escape(rest[0].strip())
        if kind == "youtube":
            vid = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
            if not vid: return ""
            return f'<figure class="embed embed--video"><iframe src="https://www.youtube-nocookie.com/embed/{vid.group(1)}" title="YouTube video" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe></figure>'
        if kind == "image":
            cap = _html.escape(rest[1].strip()) if len(rest) > 1 else ""; cred = _html.escape(rest[2].strip()) if len(rest) > 2 else ""
            return f'<figure class="embed embed--image"><img src="{url}" alt="{cap}" loading="lazy" /><figcaption>{cap}{(" — " + cred) if cred else ""}</figcaption></figure>'
        if kind == "x":
            need.add("x"); return f'<figure class="embed embed--social"><blockquote class="twitter-tweet"><a href="{url}">{url}</a></blockquote></figure>'
        if kind == "instagram":
            need.add("ig"); return f'<figure class="embed embed--social"><blockquote class="instagram-media" data-instgrm-permalink="{url}" data-instgrm-version="14"><a href="{url}">{url}</a></blockquote></figure>'
        return ""
    out = re.sub(r"^\[\[(youtube|image|x|instagram):([^\]]+)\]\]$", rep, md, flags=re.M)
    if "x" in need: out += '\n\n<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'
    if "ig" in need: out += '\n\n<script async src="https://www.instagram.com/embed.js"></script>'
    return out

def write_md(L, slug, meta, title, description, body_md):
    row, ja = meta["row"], meta["ja"]
    fm = {"title": title, "description": description[:200], "pubDate": meta["date"], "lang": L, "story": slug,
          "sourceUrl": row["url"], "sourceTitle": row["title"], "sourceName": row.get("source") or "",
          "region": row.get("region") or "", "regionEn": meta.get("regionEn") or "", "category": row.get("category") or "", "akita": bool(row.get("akita")),
          "tags": ja.get("tags", []), "sources": ja.get("sources", [])}
    if meta.get("hero"): fm["hero"] = meta["hero"]; fm["heroAlt"] = meta.get("heroAlt") or ""; fm["heroCredit"] = meta.get("heroCredit") or ""
    d = os.path.join(SITE, "src", "content", "articles", L); os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{slug}.md")
    open(path, "w").write("---\n" + "\n".join(fm_line(k, v) for k, v in fm.items()) + "\n---\n\n" + render_media(body_md.strip()) + "\n")
    return path

def run(*a, **k): return subprocess.run(a, capture_output=True, text=True, cwd=HOME, **k)

def main(slug):
    mp = os.path.join(HOME, "data", f"article_{slug}.json"); meta = json.load(open(mp)); ja = meta["ja"]
    from article import region_en
    meta["regionEn"] = region_en(meta["row"].get("region"))
    tr = translate(ja); meta["translations"] = tr; json.dump(meta, open(mp, "w"), ensure_ascii=False, indent=1)
    paths = [write_md("ja", slug, meta, ja["title"], ja["lead"], ja["body_md"])]
    for L in ("en", "nl", "de", "es"):
        paths.append(write_md(L, slug, meta, tr[L]["title"], tr[L]["description"], tr[L]["body_md"]))
    b = run("npm", "run", "build", cwd=SITE)
    if b.returncode != 0: print(b.stdout[-800:], b.stderr[-800:]); sys.exit(1)
    run("git", "checkout", "-q", "main"); run("git", "pull", "-q", "--ff-only")
    run("git", "add", *paths)
    run("git", "-c", "user.name=MIA Journal bot", "-c", "user.email=tkubo@danshiko.com", "commit", "-q", "-m", f"journal: publish {slug}")
    p = run("git", "push", "-q")
    if p.returncode != 0: print(p.stderr); sys.exit(1)
    print(f"{PUB}/ja/{slug}/")

if __name__ == "__main__":
    main(sys.argv[1])
