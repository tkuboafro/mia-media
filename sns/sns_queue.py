#!/usr/bin/env python3
"""公開済みの記事を、ソース記事が古い順に投稿枠へ入れる（久保さん 2026-10-26「古い順に順次。API 制限に引っかからないように」）。
枠の時刻（Europe/Amsterdam）に「Xに投稿」「Threadsに投稿」「IGに投稿」のチェックを1本ずつ入れるだけ。実際の投稿は sns_post_watch.py。
立ち上げ1週間（〜RAMP_END）は控えめ: X・Threads 1日4本、IG 1日1本。その後 X・Threads 6本、IG 2本。
止まっていた間の枠は埋め戻さない（一度に連投しない）。"""
import datetime as dt, json, os, sys
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notion
HOME = os.path.expanduser("~/mia-media"); TZ = ZoneInfo("Europe/Amsterdam")
STATE = os.path.join(HOME, "data", "sns", "queue_state.json")
RAMP_END = dt.date(2026, 11, 2)
SLOTS = {"ramp": {"x": ["09:00", "12:00", "15:00", "18:00"], "threads": ["09:30", "12:30", "15:30", "18:30"], "ig": ["18:00"]},
         "full": {"x": ["08:30", "10:30", "12:30", "14:30", "16:30", "18:30"], "threads": ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00"], "ig": ["12:00", "18:00"]}}
CB = {"x": "Xに投稿", "threads": "Threadsに投稿", "ig": "IGに投稿"}
TEXT = {"x": "X投稿文（Threads共用）", "threads": "X投稿文（Threads共用）", "ig": "IGキャプション"}

def published_rows():
    body = {"filter": {"and": [{"property": "チャネル", "select": {"equals": "Journal"}}, {"property": "ステータス", "select": {"equals": "投稿済み"}}]}, "page_size": 100}
    out = []
    while True:
        r = notion.api("POST", f"/data_sources/{notion.DS}/query", body); out += r["results"]
        if not r.get("has_more"): return out
        body["start_cursor"] = r["next_cursor"]

def src_date(page):
    slug = notion.prop_text(page, "記事キー").strip()
    try: return (json.load(open(f"{HOME}/data/article_{slug}.json"))["row"].get("published") or "9999")[:10]
    except Exception: return "9999"

def tick(now=None, log=print):
    now = now or dt.datetime.now(TZ); today = now.date().isoformat()
    plan = SLOTS["ramp" if now.date() < RAMP_END else "full"]
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    due = {}
    for ch, slots in plan.items():
        done = st.setdefault(ch, {}).setdefault(today, [])
        past = [s for s in slots if s <= now.strftime("%H:%M") and s not in done]
        if past: due[ch] = past
    if not due: return
    rows = sorted(published_rows(), key=src_date)
    for ch, past in due.items():
        st[ch][today] += past                     # 期限を過ぎた枠はまとめて消化扱い（連投しない）
        nxt = next((p for p in rows if not p["properties"].get(CB[ch], {}).get("checkbox") and notion.prop_text(p, TEXT[ch]).strip()), None)
        if not nxt: continue
        notion.api("PATCH", f"/pages/{nxt['id']}", {"properties": {CB[ch]: {"checkbox": True}}})
        nxt["properties"][CB[ch]] = {"checkbox": True}
        log("queue", ch, past[-1], notion.prop_text(nxt, "記事キー"))
    for ch in st: st[ch] = {d: v for d, v in st[ch].items() if d >= (now.date() - dt.timedelta(days=14)).isoformat()}
    os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(st, open(STATE, "w"), indent=1)

if __name__ == "__main__": tick()
