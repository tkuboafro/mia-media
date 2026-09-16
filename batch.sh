#!/bin/bash
# まとめて収集 → まとめて日本語原稿 → Notion＋Slack にレビュー依頼（久保さん 2026-09-16「5時半まで待たずに大量に」）
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
H="$HOME/mia-media"; LOG="$H/logs/batch_$(date +%F_%H%M).log"; PY=/usr/bin/python3
cd "$H"; echo "=== $(date '+%F %T') batch start ===" | tee -a "$LOG"
# ① 収集 4 回（テーマ×期間を変える。Grok Bot は 1 回 8 分前後）
$PY -u collect/grok_news.py --days 14 --n 15 --theme "国際コンクール受賞（IWC・Kura Master・Milano Sake Challenge・OSA など）/ 輸出・海外展開・海外の日本酒ブーム / 海外での日本酒・焼酎・ウイスキーの動き" >> "$LOG" 2>&1
$PY -u collect/grok_news.py --days 14 --n 15 --theme "蔵元の物語（代替わり・新蔵・復活・廃業・異業種参入）/ 造りの技術・新しいスタイル（低アル・スパークリング・熟成・クラフトサケ）/ 酒米・酵母の研究" >> "$LOG" 2>&1
$PY -u collect/grok_news.py --days 14 --n 15 --theme "日本のウイスキー・クラフトジン・焼酎・日本ワイン・クラフトビールの新商品・受賞・輸出（日本酒以外を中心に）" >> "$LOG" 2>&1
$PY -u collect/grok_news.py --days 30 --n 15 --theme "秋田県の酒蔵・ワイナリー・ブルワリーに関する動き（新商品・受賞・輸出・蔵元の話題）" >> "$LOG" 2>&1
echo "backlog: $(wc -l < data/backlog.jsonl)" | tee -a "$LOG"
# ② 上位 N 本を日本語原稿に → Notion ＋ Slack
N=${1:-8}
for i in $(seq 1 $N); do
  ROW=$($PY write/pick.py 2>>"$LOG")
  [ -z "$ROW" ] || [ "$ROW" = "null" ] && { echo "no more candidates" | tee -a "$LOG"; break; }
  echo "$ROW" > data/today.json
  $PY -c "import json;json.dump({'rows':[json.load(open('data/today.json'))]},open('data/today_news.json','w'),ensure_ascii=False)"
  echo "$($PY -c "import json;print(json.load(open('data/today.json'))['url'])")" >> data/used_urls.txt
  SLUG=$($PY write/article_ja.py data/today_news.json 0 2>>"$LOG" | head -1)
  [ -z "$SLUG" ] && { echo "write failed ($i)" | tee -a "$LOG"; continue; }
  URL=$($PY sns/review_request.py "$SLUG" 2>>"$LOG")
  echo "$(date '+%H:%M') [$i] $SLUG → $URL" | tee -a "$LOG"
done
echo "=== $(date '+%F %T') batch done ===" | tee -a "$LOG"
