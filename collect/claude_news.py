#!/usr/bin/env python3
"""Grok が使えない時（週次上限・ログイン切れ）の代替。`claude -p` の WebSearch で同じ JSON を作る。"""
import datetime as dt, json, os, re, subprocess, sys
HOME = os.path.expanduser("~/mia-media")
sys.path.insert(0, os.path.join(HOME, "collect"))
from grok_news import TPL, MARK, verify, SEEN

def main(n=12, akita=4, days=3):
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    prompt = TPL.format(mark=MARK, since=since, n=n, akita=akita).replace("会話タイトルは「MIA-NEWS」にしてください。", "")
    prompt += "\n必ず WebSearch / WebFetch ツールで実際に検索・確認してから答えてください。日本語で検索してください（例: 「日本酒 新商品 2026年9月」「秋田 酒蔵 受賞」「清酒 輸出 2026」）。"
    prompt += "\n手順: まず WebSearch を最低8回（テーマ×地域を変えて。うち3回以上は「秋田」を含める）行い、候補を集めてから、有望な記事を WebFetch で開いて見出し・日付・内容を確認し、確認できたものだけを出力する。ランキング記事・まとめ記事・通販ページは除外し、報道・公式発表だけにする。"
    r = subprocess.run(["claude", "-p", prompt, "--allowedTools", "WebSearch,WebFetch", "--output-format", "json", "--model", "sonnet"],
                       capture_output=True, text=True, timeout=1500)
    try:
        raw = json.loads(r.stdout).get("result", "")
    except Exception:
        raw = r.stdout
    raw = re.sub(r"```(?:json)?", "", raw)
    # 整形出力（"[\n  {"）でも拾えるように、最初の "[" から最後の "]" まで
    i = raw.find("["); j = raw.rfind("]")
    rows = []
    if i >= 0 and j > i:
        try: rows = json.loads(raw[i:j+1])
        except Exception as e: print("parse error", e); print(raw[:2000])
    open(os.path.join(HOME, "logs", "claude_news_last_raw.txt"), "w").write(raw)
    seen = set(open(SEEN).read().split()) if os.path.exists(SEEN) else set()
    out, dropped = [], []
    for row in rows:
        if not isinstance(row, dict) or not row.get("url"): continue
        if row["url"] in seen: dropped.append((row["url"], "seen")); continue
        ok, why = verify(row)
        (out if ok else dropped).append(row if ok else (row["url"], why))
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    path = os.path.join(HOME, "data", f"news_{stamp}.json")
    json.dump({"collected_at": stamp, "collector": "claude-websearch", "rows": out}, open(path, "w"), ensure_ascii=False, indent=1)
    with open(SEEN, "a") as f:
        for r_ in out: f.write(r_["url"] + "\n")
    print(f"claude rows={len(rows)} kept={len(out)} dropped={len(dropped)}")
    for d in dropped: print("  drop", d)
    for r_ in out: print("  keep", r_.get("akita"), r_.get("region"), (r_.get("title") or "")[:60])
    print(path)

if __name__ == "__main__":
    main()
