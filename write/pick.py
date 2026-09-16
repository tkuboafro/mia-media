#!/usr/bin/env python3
"""その日の記事にする1件を選ぶ。秋田を重く、直近・一次情報・EU向けの面白さで加点。"""
import json, sys, datetime as dt
W = {"受賞": 3, "輸出": 3, "新商品": 2, "蔵元": 2, "酒米": 2, "イベント": 1, "行政": 1, "研究": 2, "その他": 0}
def score(r):
    s = W.get(r.get("category") or "", 0)
    if r.get("akita"): s += 6.5
    elif "秋田" in (r.get("region") or "") + (r.get("title") or ""): s += 4
    if r.get("published"):
        try:
            age = (dt.date.today() - dt.date.fromisoformat(r["published"][:10])).days
            s += max(0, 3 - age)
        except Exception: pass
    s += min(2, len(r.get("why_eu") or "") // 15)
    if any(k in (r.get("source") or "") for k in ("公式", "酒造", "県", "新聞", "日経", "河北", "魁", "PR TIMES")): s += 1
    return s
import os
HOME = os.path.expanduser("~/mia-media")
USED = os.path.join(HOME, "data", "used_urls.txt")

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

if __name__ == "__main__":
    used = set(open(USED).read().split()) if os.path.exists(USED) else set()
    rows = [r for r in load_backlog() if r["url"] not in used]
    for p in sys.argv[1:]:
        rows += [r for r in json.load(open(p))["rows"] if r["url"] not in used]
    # 古いニュースは記事にしない（収集器が拾ってしまうことがある）
    def fresh(r):
        try: return (dt.date.today() - dt.date.fromisoformat((r.get("published") or "")[:10])).days <= 10
        except Exception: return True
    rows = [r for r in rows if fresh(r)]
    rows.sort(key=score, reverse=True)
    for r in rows[:5]: print(score(r), r.get("akita"), r.get("category"), (r.get("title") or "")[:50], file=sys.stderr)
    print(json.dumps(rows[0] if rows else None, ensure_ascii=False))
