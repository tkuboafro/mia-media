#!/usr/bin/env python3
"""その日の記事にする1件を選ぶ。
編集方針（久保さん 2026-09-16）: これは「日本のお酒事情の最新メディア」であって秋田県のプロモーションではない。
EUの読者（現地に行かない人）にとって意味がある話を選ぶ。秋田はたまに入れる程度。宿泊割引・観光キャンペーン・
地域限定イベントのような「現地にいないと意味がない」情報は選ばない。"""
import datetime as dt, json, os, sys
HOME = os.path.expanduser("~/mia-media")
USED = os.path.join(HOME, "data", "used_urls.txt")
W = {"輸出": 4, "受賞": 3, "蔵元": 3, "研究": 2, "新商品": 2, "酒米": 1, "行政": 0, "イベント": -1, "その他": 0}
LOCAL_ONLY = ("キャンペーン", "宿泊", "割引", "クーポン", "観光", "ふるさと納税", "来場", "来店", "店頭", "POP UP", "ポップアップ", "フェア", "まつり", "祭り", "抽選", "先着", "セミナー", "講座", "説明会", "講習")
GLOBAL = ("海外", "輸出", "EU", "欧州", "ヨーロッパ", "国際", "世界", "IWC", "Kura Master", "オスカー", "パリ", "ロンドン", "アムステルダム", "ベルリン", "マドリード", "ワールド", "免税", "関税")

def akita_bonus():
    """秋田は「たまに」（久保さん）。直近10本のうち秋田が3本以上なら加点をやめ、2本以上なら半分にする。"""
    files = sorted(glob.glob(os.path.join(HOME, "data", "article_*.json")), key=os.path.getmtime)[-10:]
    n = 0
    for f in files:
        try: n += bool((json.load(open(f)).get("row") or {}).get("akita"))
        except Exception: pass
    return 0.0 if n >= 3 else (1.25 if n >= 2 else 2.5)

def score(r):
    text = (r.get("title") or "") + (r.get("summary_ja") or "") + (r.get("why_eu") or "")
    s = W.get(r.get("category") or "", 0)
    s += akita_bonus() if r.get("akita") else 0
    if any(k in text for k in LOCAL_ONLY): s -= 5
    if any(k in text for k in ("日本上陸", "日本初上陸", "輸入卸", "日本発売", "日本市場に投入", "日本限定", "国内発売", "日本初登場", "輸入元", "正規輸入", "インポーター")) and not any(k in text for k in ("日本酒", "焼酎", "泡盛", "ジャパニーズ", "国産", "日本ワイン", "蔵")): s -= 6  # 海外産の酒が日本に来る話は方針外
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
    try: return (dt.date.today() - dt.date.fromisoformat((r.get("published") or "")[:10])).days <= int(os.environ.get("MIA_MAX_AGE_DAYS", "10"))  # 過去ネタの量産時は環境変数で広げる
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
        text = r.get("title", "") + " " + r.get("summary_ja", "")
        out.append((_toks(text), _bigrams(text)))
    return out

def _bigrams(t):
    t = re.sub(r"[\s、。「」『』（）()・,.:：;；!！?？\-—–/／|｜]", "", t or "")
    return {t[i:i + 2] for i in range(len(t) - 1)}

def dup_of_used(r, topics):
    """同じ出来事を別URLで拾ったものを弾く。単語一致（4語）か、文字2-gramの Jaccard（出典違いで言い回しが変わっても拾える）。"""
    text = r.get("title", "") + " " + r.get("summary_ja", "")
    t = _toks(text); b = _bigrams(text)
    for u, ub in topics:
        if len(t & u) >= 4: return True
        if b and ub and len(b & ub) / len(b | ub) >= 0.2: return True   # Jaccard。包含率だと ISC 等の長い定型句で誤爆する
    return False

def ranked(extra_files=()):
    used = set(open(USED).read().split()) if os.path.exists(USED) else set()
    topics = used_topics()
    rows = [r for r in load_backlog() if r["url"] not in used and not dup_of_used(r, topics)]
    if akita_bonus() == 0.0 and any(not r.get("akita") for r in rows):  # 秋田が直近で多すぎる間は秋田ネタを後回しにする
        rows = [r for r in rows if not r.get("akita")]
    for p in extra_files:
        rows += [r for r in json.load(open(p))["rows"] if r["url"] not in used]
    rows = [r for r in rows if fresh(r)]
    rows.sort(key=score, reverse=True)
    return rows

if __name__ == "__main__":
    rows = ranked(sys.argv[1:])
    for r in rows[:6]: print(round(score(r), 1), r.get("akita"), r.get("category"), (r.get("title") or "")[:50], file=sys.stderr)
    print(json.dumps(rows[0] if rows else None, ensure_ascii=False))
