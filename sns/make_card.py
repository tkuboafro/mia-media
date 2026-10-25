#!/usr/bin/env python3
"""The Sake Wire の IG 用カード（1080×1350 PNG）を作る。記事の英語タイトル＋カテゴリ＋（使ってよい写真があれば）写真。
写真は自社・フリー素材（写真: …）だけ。プレス画像（画像提供: …）や AI 画像は IG に使わない → その場合は文字だけのカード。
出力: site/public/sns/<slug>-ig.png（GitHub Pages で https://sakewire.com/sns/<slug>-ig.png として公開）。"""
import html, json, os, re, subprocess, sys
HOME = os.path.expanduser("~/mia-media"); OUT = os.path.join(HOME, "site", "public", "sns")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CAT = {"受賞": "Awards", "蔵元": "Breweries", "輸出": "Export", "新商品": "New releases", "研究": "Research", "行政": "Policy", "イベント": "Events"}

def usable_photo(meta):
    c = meta.get("heroCredit") or ""
    if not meta.get("hero") or "AI生成" in c or c.startswith("画像提供"): return None, None
    if c.startswith("写真"):
        who = re.sub(r"<[^>]+>", "", c.split(":", 1)[-1]).strip().replace("（", " (").replace("）", ")")
        return meta["hero"], "Photo: " + who
    return None, None

def render(meta):
    slug = meta["slug"]; tr = (meta.get("translations") or {}).get("en") or {}
    title = tr.get("title") or meta["ja"]["title"]
    cat = CAT.get((meta.get("row") or {}).get("category"), "News"); region = meta.get("regionEn") or ""
    photo, credit = usable_photo(meta)
    size = 76 if len(title) < 60 else (66 if len(title) < 85 else 58)
    desc = tr.get("description") or ""
    if not photo: size = 96 if len(title) < 60 else (84 if len(title) < 85 else 74)
    top = f'<div class="ph" style="background-image:url({html.escape(photo)})"></div>' if photo else ''
    lead = '' if photo else f'<p class="ld">{html.escape(desc)}</p>'
    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=IBM+Plex+Mono:wght@500&family=Source+Serif+4:ital,opsz,wght@1,8..60,400&display=block" rel="stylesheet">
<style>html,body{{margin:0}}.c{{width:1080px;height:1350px;background:#f6f5f1;color:#15171b;display:flex;flex-direction:column;overflow:hidden}}
.ph{{height:{'700' if photo else '420'}px;background:#ecebe5 center/cover no-repeat}}
.ph--type{{display:flex;align-items:flex-end;padding:0 72px 40px;background:#15171b;color:#f6f5f1;font:700 54px/1 'Fraunces',serif;box-sizing:border-box}}
.b{{flex:1;padding:{'56px' if photo else '120px'} 72px 64px;display:flex;flex-direction:column;box-sizing:border-box}}
.dl{{font:500 24px/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#676c74}} .dl b{{color:#23406b;font-weight:500}}
h1{{font:600 {size}px/1.06 'Fraunces',serif;letter-spacing:-.015em;margin:{'26px' if photo else '48px'} 0 0}}
.ld{{font:italic 400 38px/1.4 'Source Serif 4',Georgia,serif;color:#2a2d33;margin:44px 0 0;max-width:40ch}}
.ft{{margin-top:auto;display:flex;justify-content:space-between;align-items:flex-end;font:500 22px/1.3 'IBM Plex Mono',monospace;color:#676c74;letter-spacing:.06em}}
.wm{{font:700 40px/1 'Fraunces',serif;color:#15171b;letter-spacing:0}} .rule{{width:120px;height:4px;background:#c9351f;margin:0 0 16px}}</style></head>
<body><div class="c">{top}<div class="b"><div class="dl"><b>{html.escape(cat)}</b>{(' · ' + html.escape(region)) if region else ''}</div>
<h1>{html.escape(title)}</h1>{lead}<div class="ft"><div><div class="rule"></div><div class="wm">The Sake Wire</div></div>
<div style="text-align:right">{html.escape(credit) + '<br>' if credit else ''}sakewire.com · 18+</div></div></div></div></body></html>"""
    os.makedirs(OUT, exist_ok=True); src = os.path.join(OUT, f".{slug}.html"); png = os.path.join(OUT, f"{slug}-ig.png")
    open(src, "w").write(doc)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=15000",
                    "--window-size=1080,1350", f"--screenshot={png}", "file://" + src], capture_output=True, timeout=120)
    os.remove(src)
    if not os.path.exists(png): raise RuntimeError("card render failed")
    return png, f"https://sakewire.com/sns/{slug}-ig.png"

if __name__ == "__main__":
    print(render(json.load(open(f"{HOME}/data/article_{sys.argv[1]}.json"))))
