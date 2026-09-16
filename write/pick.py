#!/usr/bin/env python3
"""その日の記事にする1件を選ぶ。
編集方針（久保さん 2026-09-16）: これは「日本のお酒事情の最新メディア」であって秋田県のプロモーションではない。
EUの読者（現地に行かない人）にとって意味がある話を選ぶ。秋田はたまに入れる程度。宿泊割引・観光キャンペーン・
地域限定イベントのような「現地にいないと意味がない」情報は選ばない。"""
import datetime as dt, json, os, sys
HOME = os.path.expanduser("~/mia-media")
USED = os.path.join(HOME, "data", "used_urls.txt")
W = {"輸出": 4, "受賞": 3, "蔵元": 3, "研究": 2, "新商品": 2, "酒米": 1, "行政": 0, "イベント": -1, "その他": 0}
LOCAL_ONLY = ("キャンペーン", "宿泊", "割引", "クーポン", "観光", "ふるさと納税", "来場", "来店", "店頭", "POP UP", "ポップアップ", "フェア", "まつり", "祭り", "抽選", "先着")
GLOBAL = ("海外", "輸出", "EU", "欧州", "ヨーロッパ", "国際", "世界", "IWC", "Kura Master", "オスカー", "パリ", "ロンドン", "アムステルダム", "ベルリン", "マドリード", "ワールド", "免税", "関税")

def score(r):
    text = (r.get("title") or "") + (r.get("summary_ja") or "") + (r.get("why_eu") or "")
    s = W.get(r.get("category") or "", 0)
    s += 2.5 if r.get("akita") else 0
    if any(k in text for k in LOCAL_ONLY): s -= 5
    s += 3 * min(2, sum(1 for k in GLOBAL if k in text))
    if r.get("published"):
        try: s += max(0, 3 - (dt.date.today() - dt.date.fromisoformat(r["published"][:10])).days)
        except Exception: pass
    if any(k in (r.get("source") or "") for k in ("公式", "酒造", "新聞", "日経", "河北", "魁", "PR TIMES", "蒸溜所")): s += 1
    return s

def load_backlog():
    p = os.path.join(HOME, "data", "backlog.jsonl")
    if not os.path.exists(p): return []
    rows, seen = [], set()
    for line in open(p):
        try: r = json.loads(line)
        except Exception: continue
        if r.get("url") and r["url"] not in seen:
            seen.add(r["url"]); rows.append(r)
    return rows

def fresh(r):
    try: return (dt.date.today() - dt.date.fromisoformat((r.get("published") or "")[:10])).days <= 10
    except Exception: return True

import re, glob
def _toks(t):
    return {x for x in re.findall(r"[一-龠ァ-ヶA-Za-z0-9]{2,}", t or "") if x not in ("日本酒", "発売", "開催", "限定", "新商品", "2026", "受賞", "株式会社", "酒造")}

def used_topics():
    """すでに記事にした出来事のトークン集合（同じニュースを別URLで拾っても記事を重複させない）"""
    out = []
    for f in glob.glob(os.path.join(HOME, "data", "article_*.json")):
        try: r = json.load(open(f)).get("row") or {}
        except Exception: continue
        out.append(_toks(r.get("title", "") + " " + r.get("summary_ja", "")))
    return out

def dup_of_used(r, topics):
    t = _toks(r.get("title", "") + " " + r.get("summary_ja", ""))
    return any(len(t & u) >= 4 for u in topics)

def ranked(extra_files=()):
    used = set(open(USED).read().split()) if os.path.exists(USED) else set()
    topics = used_topics()
    rows = [r for r in load_backlog() if r["url"] not in used and not dup_of_used(r, topics)]
    for p in extra_files:
        rows += [r for r in json.load(open(p))["rows"] if r["url"] not in used]
    rows = [r for r in rows if fresh(r)]
    rows.sort(key=score, reverse=True)
    return rows

if __name__ == "__main__":
    rows = ranked(sys.argv[1:])
    for r in rows[:6]: print(round(score(r), 1), r.get("akita"), r.get("category"), (r.get("title") or "")[:50], file=sys.stderr)
    print(json.dumps(rows[0] if rows else None, ensure_ascii=False))
