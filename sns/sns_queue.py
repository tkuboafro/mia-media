#!/usr/bin/env python3
"""公開済みの記事を、ソース記事が古い順に「Xに投稿」「Threadsに投稿」「IGに投稿」へ1本ずつ入れる。実際の投稿は sns_post_watch.py。
久保さん 2026-10-26「古い順に順次。API 制限に引っかからないように」→ 同日「はやくおわらせて」で時刻枠をやめ、各サービスの上限の手前まで詰めた間隔で回す。
  X（Buffer 経由）    : X の上限 2,400件/日 → 5分間隔・24時間で280件まで
  Threads（API 直接） : 250件/24時間       → 6分間隔・235件まで
  IG（Buffer 経由）   : 100件/24時間       → 15分間隔・90件まで
止まっていた間の分は埋め戻さない（1回の巡回で1チャネル1本まで）。"""
import datetime as dt, json, os, sys
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notion
HOME = os.path.expanduser("~/mia-media"); TZ = ZoneInfo("Europe/Amsterdam")
STATE = os.path.join(HOME, "data", "sns", "queue_state.json")
# Buffer 無料プランは API 250 リクエスト/24h。1投稿 = 作成1回＋確認1回なので X+IG で 100本/日が上限。
# X は 2026-10-26 に51本目で 403（自動投稿扱い）→ 再開後は 30分間隔・40本/日。IG は 24分間隔・60本/日。
INTERVAL = {"x": 30, "threads": 6, "ig": 24}   # 分
CAP24 = {"x": 40, "threads": 235, "ig": 60}
RETRY = os.path.join(HOME, "data", "sns", "buffer_retry_at")   # 429 を受けた時に見張りが書く「この時刻まで Buffer を呼ばない」
def buffer_blocked():
    try: return os.path.exists(RETRY) and dt.datetime.now().timestamp() < float(open(RETRY).read().strip() or 0)
    except Exception: return False
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
    now = now or dt.datetime.now(TZ)
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    hist = st.get("sent_at", {}); due = []
    for ch, gap in INTERVAL.items():
        if os.path.exists(os.path.join(HOME, "data", "sns", f"pause_{ch}")): continue   # 久保さんが再接続するまで止める等
        if ch in ("x", "ig") and buffer_blocked(): continue   # Buffer の日次上限待ち
        h = [t for t in hist.get(ch, []) if now - dt.datetime.fromisoformat(t) < dt.timedelta(hours=24)]; hist[ch] = h
        if h and now - dt.datetime.fromisoformat(h[-1]) < dt.timedelta(minutes=gap) - dt.timedelta(seconds=30): continue
        if len(h) >= CAP24[ch]: continue
        due.append(ch)
    if due:
        rows = sorted(published_rows(), key=src_date)
        for ch in due:
            nxt = next((p for p in rows if not p["properties"].get(CB[ch], {}).get("checkbox") and notion.prop_text(p, TEXT[ch]).strip()), None)
            if not nxt: continue
            notion.api("PATCH", f"/pages/{nxt['id']}", {"properties": {CB[ch]: {"checkbox": True}}})
            nxt["properties"][CB[ch]] = {"checkbox": True}; hist[ch].append(now.isoformat())
            log("queue", ch, f"{len(hist[ch])}/24h", notion.prop_text(nxt, "記事キー"))
    os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump({"sent_at": hist}, open(STATE, "w"), indent=1)

if __name__ == "__main__": tick()
