#!/usr/bin/env python3
"""その日の記事にする1件を選ぶ。秋田を重く、直近・一次情報・EU向けの面白さで加点。"""
import json, sys, datetime as dt
W = {"受賞": 3, "輸出": 3, "新商品": 2, "蔵元": 2, "酒米": 2, "イベント": 1, "行政": 1, "研究": 2, "その他": 0}
def score(r):
    s = W.get(r.get("category") or "", 0)
    if r.get("akita"): s += 5
    elif "秋田" in (r.get("region") or "") + (r.get("title") or ""): s += 4
    if r.get("published"):
        try:
            age = (dt.date.today() - dt.date.fromisoformat(r["published"][:10])).days
            s += max(0, 3 - age)
        except Exception: pass
    s += min(2, len(r.get("why_eu") or "") // 15)
    if any(k in (r.get("source") or "") for k in ("公式", "酒造", "県", "新聞", "日経", "河北", "魁", "PR TIMES")): s += 1
    return s
if __name__ == "__main__":
    rows = []
    for p in sys.argv[1:]:
        rows += json.load(open(p))["rows"]
    rows.sort(key=score, reverse=True)
    for r in rows[:5]: print(score(r), r.get("akita"), r.get("category"), (r.get("title") or "")[:50], file=sys.stderr)
    print(json.dumps(rows[0] if rows else None, ensure_ascii=False))
