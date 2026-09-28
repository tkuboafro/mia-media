#!/usr/bin/env python3
"""日本のお酒ニュースを grok.com の画面から集める（xAI API は使わない。~/.local/danshiko/xgrok/run.py と同じ手口）。

* 常駐ブラウザ ~/.local/share/danshiko/claude_browser/cmd.sh を使う。共用なので落とさない・閉じない。
* xgrok（21:00 現地、tab10〜15）と時間・タブをずらす。ここは「MIA」で始まる会話タブか tab9 を使う。
* Grok の申告は信用しない: URL は実際に GET して 200 かつ本文に見出し語が含まれるものだけ採用。
"""
import base64, datetime as dt, json, os, re, subprocess, sys, time, urllib.request

CMD = os.path.expanduser("~/.local/share/danshiko/claude_browser/cmd.sh")
HOME = os.path.expanduser("~/mia-media")
SEEN = os.path.join(HOME, "data", "seen_urls.txt")
MARK = "MIA-NEWS"
# Grok Bot は通常チャットの週次上限に掛からない（2026-09-16 実測）。久保さん作成のボットで会話する。
BOT_URL = os.environ.get("MIA_GROK_URL", "https://grok.com/bot/db26fca6-5bcb-44d3-b570-6a9e743785bb")

TPL = """依頼ID: {nonce}（このボット内の以前のやり取りは無視して、今回の依頼だけに答えてください）
あなたは日本の酒類業界ニュースのリサーチャーです。会話タイトルは「{mark}」にしてください。
{since}から{until}までの間に公開された、日本のお酒（日本酒・焼酎・日本ワイン・クラフトビール・クラフトジン・ウイスキー・梅酒など）に関する
**日本語の一次情報**（蔵元・メーカーの公式発表、新聞・業界紙・自治体・コンテストの公式ページ）を Web 検索で探し、
{n}件をJSONで出力してください。読者はヨーロッパ在住で日本に行かない人なので、**海外でも意味のある話**（国際コンクール受賞、輸出・海外展開、造り手や技術の話、新しいスタイル、業界の動き）を優先し、宿泊割引・観光キャンペーン・来店イベントのような現地限定の情報は除いてください。秋田県に関するものがあれば{akita}件程度含めてください。

探す主なテーマ: {theme}
{exclude}
必ず今回あらためて Web 検索してください（記憶や以前の回答の使い回しは不可）。published が {since}〜{until} の範囲外のものは含めないでください。

出力形式（この配列だけを返す。前置き・説明・コードフェンスは不要）:
[{{"title":"記事の見出し（原文のまま）","url":"記事URL","source":"媒体名","published":"YYYY-MM-DD","summary_ja":"120字以内の要約","region":"都道府県名 or 全国","category":"新商品|受賞|輸出|蔵元|酒米|イベント|行政|研究|その他","akita":true/false,"why_eu":"EUの読者にとって面白い点を40字以内で"}}]

厳守:
- 実在するURLだけ。記事を実際に開いて確認した見出しと日付だけを書く。推測で書かない。
- 同じ出来事は1件にまとめる。
- published は記事の公開日（不明なら null）。
"""

def br(payload, timeout=120):
    try:
        r = subprocess.run([CMD, json.dumps(payload, ensure_ascii=False)], capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR {type(e).__name__}"

def js(tab, code):
    return br({"action": "eval", "tab": tab, "js": code})

def tabs():
    out = br({"action": "tabs"})
    res = []
    for line in out.splitlines():
        m = re.match(r"tab(\d+) (\S+) (.*?)\s{2}(\S+)$", line)
        if m:
            res.append((int(m.group(1)), m.group(3).strip(), m.group(4)))
    return res

def pick_tab():
    """ボットのタブ → MIA の会話タブ → tab9 の grok ホーム → 新規タブ。10〜15 は xgrok の領域なので触らない。"""
    for i, title, url in tabs():
        if url.startswith(BOT_URL) and i not in range(10, 16):
            return i
    for i, title, url in tabs():
        if "grok.com" in url and title.startswith(MARK) and i not in range(10, 16):
            return i
    for i, title, url in tabs():
        if i == 9 and url.rstrip("/") == "https://grok.com":
            return i
    br({"action": "goto", "url": "https://grok.com/", "wait": 3000})
    t = tabs()
    return t[-1][0] if t else None

def new_chat(tab):
    """スレッドが伸び続けると古い答えを拾うので、毎回 New chat から始める。"""
    js(tab, "(()=>{const b=Array.from(document.querySelectorAll('a,button')).find(e=>/^new chat$/i.test((e.getAttribute('aria-label')||e.innerText||'').trim()));if(b){b.click();return 'new';}return 'none';})()")
    time.sleep(2)

BUSY_JS = "(()=>{const b=Array.from(document.querySelectorAll('button')).find(e=>/stop/i.test(e.getAttribute('aria-label')||''));return b?'busy':'idle'})()"
STOP_JS = "(()=>{const b=Array.from(document.querySelectorAll('button')).find(e=>/stop/i.test(e.getAttribute('aria-label')||''));if(b){b.click();return 'stopped'}return 'none'})()"

def wait_idle(tab, max_s=600):
    """前の依頼がまだ生成中なら待つ。待ちきれなければ生成を止める（依頼が積み重なると Grok が混乱する）。"""
    t0 = time.time()
    while time.time() - t0 < max_s:
        if js(tab, BUSY_JS).strip().strip('"') != "busy": return True
        time.sleep(15)
    print("grok still busy — stopping previous generation", flush=True)
    js(tab, STOP_JS); time.sleep(3)
    return False

def send(tab, prompt, nonce):
    b64 = base64.b64encode(prompt.encode()).decode()
    for attempt in range(3):
        js(tab, "(()=>{const t=decodeURIComponent(escape(atob('" + b64 + "')));"
                "const el=document.querySelector('.ProseMirror[contenteditable=true]');"
                "if(!el)return 'nc';el.focus();document.execCommand('selectAll',false,null);"
                "document.execCommand('insertText',false,t);return el.innerText.length;})()")
        time.sleep(1)
        r = js(tab, "(()=>{const el=document.querySelector('.ProseMirror[contenteditable=true]');"
                    "const f=el&&el.closest('form');const s=(f||document).querySelector('button[type=submit]');"
                    "if(s){s.click();return 'sent';}"
                    "el.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',keyCode:13,bubbles:true}));return 'enter';})()")
        for _ in range(8):   # 送信できていれば本文に依頼IDが現れる
            time.sleep(2)
            t = body_text(tab)
            ed = js(tab, "(()=>{const el=document.querySelector('.ProseMirror[contenteditable=true]');return el?el.innerText.trim().length:0})()").strip().strip('"')
            if isinstance(t, str) and nonce in t and ed.isdigit() and int(ed) <= 1: return f"{r}/ok{attempt}"
        print(f"send retry {attempt}: {r}", flush=True)
    return "unsent"

def body_len(tab):
    v = js(tab, "document.body.innerText.length").strip().strip('"')
    return int(v) if v.isdigit() else -1

def body_text(tab):
    out = js(tab, "document.body.innerText")
    try:
        return json.loads(out)
    except Exception:
        return out

LIMIT_RE = re.compile(r"hit your (weekly|daily) limit|usage limit|Resets [A-Z][a-z]+ \d", re.I)

def capped(tab):
    """Grok の上限表示（"You've hit your weekly limit / Resets September 18"）が出ていれば True。"""
    t = body_text(tab)
    return bool(LIMIT_RE.search(t if isinstance(t, str) else ""))

MARKER = "published は記事の公開日（不明なら null）。"

def answer_text(tab, nonce=None):
    """スレッドは伸び続けるので、今回の依頼ID（無ければ MARKER）より後ろだけを答えとして見る。"""
    t = body_text(tab)
    if not isinstance(t, str): return ""
    key = nonce or MARKER
    i = t.rfind(key)
    if i < 0: return ""
    rest = t[i + len(key):]
    j = rest.find(MARKER)          # 依頼文の末尾までは飛ばす
    return rest[j + len(MARKER):] if j >= 0 else rest

def wait_done(tab, base, max_s=1500, nonce=None):
    """答えの中に JSON 配列が現れ、かつ本文が2回連続で変化しなくなったら完了。実測: ボットは検索込みで7〜8分。"""
    t0, prev, stab = time.time(), -1, 0
    while time.time() - t0 < max_s:
        if capped(tab):
            print("GROK_CAPPED", flush=True)
            return False
        ans = answer_text(tab, nonce); n = len(ans)
        stab = stab + 1 if n == prev else 0
        prev = n
        if stab >= 2 and re.search(r'\[\s*\{\s*"title"', ans):
            return True
        time.sleep(10)
    return False

def parse(raw):
    i = raw.rfind("[\n{")
    if i < 0: i = raw.rfind("[{")
    if i < 0: i = raw.rfind("[\n  {")
    if i < 0:
        return []
    depth, j = 0, i
    for j in range(i, len(raw)):
        if raw[j] == "[": depth += 1
        elif raw[j] == "]":
            depth -= 1
            if depth == 0: break
    chunk = raw[i:j + 1]
    try:
        rows = json.loads(chunk)
    except Exception:
        rows = []
        for m in re.finditer(r"\{.*?\}", chunk, re.S):
            try: rows.append(json.loads(m.group(0)))
            except Exception: pass
    return [r for r in rows if isinstance(r, dict) and r.get("url")]

def verify(row):
    """URL が本当に生きていて、見出し語の一部が本文にあるか。"""
    url = row["url"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MIA news check)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            if r.status != 200: return False, f"http {r.status}"
            body = r.read(400000)
    except Exception as e:
        return False, f"fetch {type(e).__name__}"
    for enc in ("utf-8", "shift_jis", "euc-jp"):
        try: text = body.decode(enc); break
        except Exception: text = ""
    text = re.sub(r"<[^>]+>", " ", text)
    title = row.get("title") or ""
    toks = [t for t in re.findall(r"[一-龠ぁ-んァ-ンA-Za-z0-9]{2,}", title)]
    hit = sum(1 for t in toks if t in text)
    ok = toks and hit / len(toks) >= 0.4
    return ok, f"title-tokens {hit}/{len(toks)}"

DEFAULT_THEME = "新商品・限定酒 / 受賞（IWC, Kura Master, 全国新酒鑑評会, SAKE COMPETITION など）/ 輸出・海外展開 / 蔵元の代替わり・新蔵・廃業 / 酒米・酒造好適米 / 研究・技術 / 業界の動き"

def known_titles(k=40):
    """既に持っているネタの見出し（直近 k 件）。Grok に「これは除外」と渡して同じ物を返させない。"""
    try:
        rows = [json.loads(l) for l in open(os.path.join(HOME, "data", "backlog.jsonl"))]
    except FileNotFoundError: return []
    return [r.get("title", "")[:40] for r in rows[-k:] if r.get("title")]

def main(n=15, akita=2, days=3, theme=DEFAULT_THEME, until=None):
    seen = set(open(SEEN).read().split()) if os.path.exists(SEEN) else set()
    tab = pick_tab()
    if tab is None:
        print("no tab"); sys.exit(1)
    until = until or dt.date.today().isoformat()
    since = (dt.date.fromisoformat(until) - dt.timedelta(days=days)).isoformat()
    kt = known_titles()
    exclude = ("既に把握済みなので除外する見出し:\n" + "\n".join(f"- {t}" for t in kt) + "\n") if kt else ""
    br({"action": "goto", "tab": tab, "url": BOT_URL, "wait": 4000})
    nonce = "MIA" + dt.datetime.now().strftime("%Y%m%d%H%M%S")
    wait_idle(tab)
    base = body_len(tab)
    r = send(tab, TPL.format(nonce=nonce, mark=MARK, since=since, until=until, n=n, akita=akita, theme=theme, exclude=exclude), nonce)
    print(f"tab{tab} send={r} base={base} nonce={nonce}", flush=True)
    if r == "unsent":
        print("could not send prompt to Grok", flush=True); sys.exit(2)
    if not wait_done(tab, base, nonce=nonce):
        if capped(tab):
            # 久保さん方針(2026-09-16): 上限に当たったら収集は止める。Claude 検索への代替はしない（トークンを使うため）。
            print("Grok weekly/daily limit reached — no collection today", flush=True)
            sys.exit(3)
        print("timeout waiting for Grok — stopping generation", flush=True); js(tab, STOP_JS)
    rows = parse(answer_text(tab, nonce))
    out, dropped = [], []
    for row in rows:
        if row["url"] in seen:
            dropped.append((row["url"], "seen")); continue
        ok, why = verify(row)
        (out if ok else dropped).append(row if ok else (row["url"], why))
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    path = os.path.join(HOME, "data", f"news_{stamp}.json")
    json.dump({"collected_at": stamp, "rows": out}, open(path, "w"), ensure_ascii=False, indent=1)
    with open(SEEN, "a") as f:
        for r_ in out: f.write(r_["url"] + "\n")
    # バックログに溜める。記事は1日1本なので、取れた日に多めに取っておけば上限の日も更新できる
    with open(os.path.join(HOME, "data", "backlog.jsonl"), "a") as f:
        for r_ in out:
            r_["collected_at"] = stamp
            f.write(json.dumps(r_, ensure_ascii=False) + "\n")
    print(f"grok rows={len(rows)} kept={len(out)} dropped={len(dropped)} -> {path}", flush=True)
    for d in dropped: print("  drop", d, flush=True)
    for r_ in out: print("  keep", r_.get("akita"), r_.get("region"), r_.get("title")[:60], flush=True)
    print(path)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int, default=3); ap.add_argument("--n", type=int, default=15); ap.add_argument("--theme", default=DEFAULT_THEME); ap.add_argument("--until", default=None)
    a = ap.parse_args(); main(n=a.n, days=a.days, theme=a.theme, until=a.until)
