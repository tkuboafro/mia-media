#!/usr/bin/env python3
"""確認待ち原稿の画像点検（2026-10-10 久保さん「一昨日以前の原稿の画像を再チェック、AI画像は直す」）。
モデルは呼ばない。Notion の確認待ち × 原稿 JSON を見て、AI 画像・リンク切れ・ヒーロー無し・画像の無い見出しを数える。
使い方: audit_media.py [--before 2026-10-09]  → data/audit/media_audit.json"""
import json, os, re, sys, concurrent.futures as cf, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sns")); import notion
HOME = os.path.expanduser("~/mia-media")
BEFORE = sys.argv[sys.argv.index("--before") + 1] if "--before" in sys.argv else "2026-10-09"
IMG = re.compile(r"^\[\[image:([^\]|]+)(?:\|([^\]|]*))?(?:\|([^\]]*))?\]\]\s*$", re.M)
MEDIA = re.compile(r"^\[\[(?:image|youtube|x|instagram):", re.M)
AI = re.compile(r"fal\.(?:media|ai|run)|AI生成")

def status(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (TheSakeWire media audit)", "Range": "bytes=0-1023"})
        with urllib.request.urlopen(req, timeout=20) as r: return r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e: return e.code, ""
    except Exception as e: return 0, type(e).__name__

def sections(md):
    """見出しごとに、直後（次の見出しまで）にメディアがあるか。"""
    out = []; parts = re.split(r"^## ", md, flags=re.M)
    for p in parts[1:]:
        head = p.splitlines()[0].strip(); out.append((head, bool(MEDIA.search(p))))
    return out

pages = [p for p in notion.pending_pages(include_waiting=True) if notion.prop_select(p, "ステータス") == "確認待ち"]
rows = []
for p in pages:
    slug = notion.prop_text(p, "記事キー").strip()
    if not slug or slug[:10] >= BEFORE: continue
    mp = os.path.join(HOME, "data", f"article_{slug}.json")
    if not os.path.exists(mp): rows.append({"slug": slug, "error": "no meta"}); continue
    m = json.load(open(mp)); ja = m["ja"]; body = ja.get("body_md") or ""
    imgs = [(u.strip(), (c or "").strip(), (cr or "").strip()) for u, c, cr in IMG.findall(body)]
    hero = m.get("hero"); hc = m.get("heroCredit") or ""
    secs = sections(body)
    rows.append({"slug": slug, "page": p["id"], "edited_by_person": (p.get("last_edited_by") or {}).get("type") == "person",
                 "title": ja.get("title"), "hero": hero, "hero_ai": bool(hero and AI.search((hero or "") + hc)),
                 "imgs": imgs, "ai_imgs": [u for u, c, cr in imgs if AI.search(u + "|" + cr)],
                 "h2": len(secs), "h2_without_media": [h for h, ok in secs if not ok]})
urls = sorted({u for r in rows for u, _, _ in r.get("imgs", [])} | {r["hero"] for r in rows if r.get("hero")})
with cf.ThreadPoolExecutor(16) as ex: st = dict(zip(urls, ex.map(status, urls)))
for r in rows:
    if "imgs" not in r: continue
    r["broken"] = [u for u, _, _ in r["imgs"] if st[u][0] not in (200, 206)]
    r["hero_broken"] = bool(r["hero"] and st[r["hero"]][0] not in (200, 206))
json.dump({"before": BEFORE, "rows": rows, "status": {u: s for u, s in st.items() if s[0] not in (200, 206)}},
          open(os.path.join(HOME, "data", "audit", "media_audit.json"), "w"), ensure_ascii=False, indent=1)
ok = [r for r in rows if "imgs" in r]
print("対象", len(rows), "| meta無し", len(rows) - len(ok), "| Notionを人が編集", sum(r["edited_by_person"] for r in ok))
print("AI画像あり", sum(1 for r in ok if r["ai_imgs"] or r["hero_ai"]), "| リンク切れあり", sum(1 for r in ok if r["broken"] or r["hero_broken"]),
      "| ヒーロー無し", sum(1 for r in ok if not r["hero"]), "| 画像の無い見出しあり", sum(1 for r in ok if r["h2_without_media"]),
      "| 画像の無い見出し 合計", sum(len(r["h2_without_media"]) for r in ok), "/ 見出し合計", sum(r["h2"] for r in ok))
print("壊れたURLの状態:", sorted({str(s) for s in st.values() if s[0] not in (200, 206)}))
