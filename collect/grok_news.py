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

TPL = """あなたは日本の酒類業界ニュースのリサーチャーです。会話タイトルは「{mark}」にしてください。
{since}以降に公開された、日本のお酒（日本酒・焼酎・日本ワイン・クラフトビール・クラフトジン・ウイスキー・梅酒など）に関する
**日本語の一次情報**（蔵元・メーカーの公式発表、新聞・業界紙・自治体・コンテストの公式ページ）を Web 検索で探し、
{n}件をJSONで出力してください。**秋田県に関するものを優先して最低{akita}件**含めてください（秋田の蔵元・秋田県の施策・秋田の酒米・秋田のコンテスト受賞など）。

探す主なテーマ: 新商品・限定酒 / 受賞（IWC, Kura Master, 全国新酒鑑評会, SAKE COMPETITION など）/ 輸出・海外展開 / 蔵元の代替わり・新蔵・廃業 / 酒米・酒造好適米 / 酒蔵ツーリズム・イベント / 行政・税制 / 研究・技術

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
    """MIA の会話タブ → tab9 の grok ホーム → 新規タブ。10〜15 は xgrok の領域なので触らない。"""
    for i, title, url in tabs():
        if "grok.com" in url and title.startswith(MARK) and i not in range(10, 16):
            return i
    for i, title, url in tabs():
        if i == 9 and url.rstrip("/") == "https://grok.com":
            return i
    br({"action": "goto", "url": "https://grok.com/", "wait": 3000})
    t = tabs()
    return t[-1][0] if t else None

def send(tab, prompt):
    b64 = base64.b64encode(prompt.encode()).decode()
    js(tab, "(()=>{const t=decodeURIComponent(escape(atob('" + b64 + "')));"
            "const el=document.querySelector('.ProseMirror[contenteditable=true]');"
            "if(!el)return 'nc';el.focus();document.execCommand('selectAll',false,null);"
            "document.execCommand('insertText',false,t);return el.innerText.length;})()")
    return js(tab, "(()=>{const s=Array.from(document.querySelectorAll('button')).find(e=>e.type==='submit');"
                   "if(s){s.click();return 'sent';} return 'ng';})()")

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

def wait_done(tab, base, max_s=480):
    t0, prev, stab = time.time(), -1, 0
    while time.time() - t0 < max_s:
        if int(time.time() - t0) % 24 < 8 and capped(tab):
            print("GROK_CAPPED", flush=True)
            return False
        n = body_len(tab)
        if n >= 0:
            stab = stab + 1 if n == prev else 0
            prev = n
            if stab >= 3 and n > base + 800:
                return True
        time.sleep(8)
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

def main(n=15, akita=5, days=3):
    seen = set(open(SEEN).read().split()) if os.path.exists(SEEN) else set()
    tab = pick_tab()
    if tab is None:
        print("no tab"); sys.exit(1)
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    br({"action": "goto", "tab": tab, "url": "https://grok.com/", "wait": 3000})
    base = body_len(tab)
    r = send(tab, TPL.format(mark=MARK, since=since, n=n, akita=akita))
    print(f"tab{tab} send={r} base={base}", flush=True)
    if not wait_done(tab, base):
        if capped(tab):
            # 久保さん方針(2026-09-16): 上限に当たったら収集は止める。Claude 検索への代替はしない（トークンを使うため）。
            print("Grok weekly/daily limit reached — no collection today", flush=True)
            sys.exit(3)
        print("timeout waiting for Grok", flush=True)
    rows = parse(body_text(tab))
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
    main()
