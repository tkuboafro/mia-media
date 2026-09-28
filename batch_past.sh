#!/bin/bash
# 過去 90 日のネタをまとめて収集 → まとめて日本語原稿（久保さん 2026-09-28「過去の情報拾ってくる形で大量に」）
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export MIA_MAX_AGE_DAYS=120
H="$HOME/mia-media"; LOG="$H/logs/batch_past_$(date +%F_%H%M).log"; PY=/usr/bin/python3
cd "$H"; echo "=== $(date '+%F %T') batch_past start ===" | tee -a "$LOG"
D=${DAYS:-90}
THEMES=(
"国際コンクールの受賞（IWC 2026・Kura Master・SAKE COMPETITION・Milano Sake Challenge・IWSC・ISC・Oriental Sake Awards・全国新酒鑑評会）— 受賞蔵と銘柄、審査の背景"
"日本酒・焼酎・ウイスキーの輸出と海外展開（EU・米国・アジアの市場、関税や規制、海外の提携・海外での醸造、輸出統計）"
"蔵元の物語（代替わり・若手や女性の杜氏・新しい蔵の開業・休止や廃業からの復活・異業種からの参入・海外出身の醸造家）"
"造りの技術と研究（酵母や酒米の開発、低アルコール・スパークリング・熟成・木桶・生酛、クラフトサケ、大学や研究機関との共同研究）"
"ジャパニーズウイスキーとクラフトジン（新しい蒸留所、国際的な受賞、限定ボトル、輸出、蒸留所の設備投資）"
"日本ワインとクラフトビールと本格焼酎（国際的な受賞、輸出、新しいスタイル、産地やブドウ品種の動き）"
"業界と制度（GI 地理的表示、酒税、ユネスコ無形文化遺産『伝統的酒造り』、免税やインバウンド、後継者問題、業界団体の統計）"
"秋田県の酒蔵・ワイナリー・ブルワリーの動き（新商品・受賞・輸出・蔵元の話題）"
)
for T in "${THEMES[@]}"; do
  $PY -u collect/grok_news.py --days $D --n 15 --theme "$T" >> "$LOG" 2>&1; echo "$(date '+%H:%M') collected: $(wc -l < data/backlog.jsonl) rows" | tee -a "$LOG"
done
echo "CANDIDATES: $($PY -c "import sys;sys.path.insert(0,'write');import pick;print(len(pick.ranked()))" 2>>"$LOG")" | tee -a "$LOG"
N=${1:-30}
for i in $(seq 1 $N); do
  ROW=$($PY write/pick.py 2>>"$LOG")
  [ -z "$ROW" ] || [ "$ROW" = "null" ] && { echo "no more candidates" | tee -a "$LOG"; break; }
  echo "$ROW" > data/today.json
  $PY -c "import json;json.dump({'rows':[json.load(open('data/today.json'))]},open('data/today_news.json','w'),ensure_ascii=False)"
  echo "$($PY -c "import json;print(json.load(open('data/today.json'))['url'])")" >> data/used_urls.txt
  SLUG=$($PY write/article_ja.py data/today_news.json 0 2>>"$LOG" | head -1)
  [ -z "$SLUG" ] && { echo "write failed ($i)" | tee -a "$LOG"; continue; }
  URL=$($PY sns/review_request.py "$SLUG" 2>>"$LOG")
  echo "$(date '+%H:%M') WROTE [$i] $SLUG → $URL" | tee -a "$LOG"
done
echo "=== $(date '+%F %T') batch_past done ===" | tee -a "$LOG"
