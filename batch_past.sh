#!/bin/bash
# 過去ネタの量産: 月ごとの窓 × テーマで Grok 収集（同じ物を返させない）→ まとめて日本語原稿（久保さん 2026-09-28）
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export MIA_MAX_AGE_DAYS=${MIA_MAX_AGE_DAYS:-120}
H="$HOME/mia-media"; LOG="$H/logs/batch_past_$(date +%F_%H%M).log"; PY=/usr/bin/python3
cd "$H"; echo "=== $(date '+%F %T') batch_past start ===" | tee -a "$LOG"
WINDOWS=(${MIA_WINDOWS:-"2026-07-31 31" "2026-08-31 31" "2026-09-14 14"})   # until days（MIA_WINDOWS で上書き可）
THEMES=(
"国際コンクールの受賞（IWC・Kura Master・SAKE COMPETITION・Milano Sake Challenge・IWSC・ISC・全国新酒鑑評会）と、日本酒・焼酎・ウイスキーの輸出・海外展開（EU・米国・アジア、関税や規制、海外提携）"
"蔵元の物語（代替わり・若手や女性の杜氏・新しい蔵の開業・休止や廃業からの復活・異業種や海外出身の醸造家）と、造りの技術・研究（酵母や酒米、低アル・スパークリング・熟成・木桶・生酛、クラフトサケ、大学との共同研究）"
"ジャパニーズウイスキー・クラフトジン・日本ワイン・クラフトビール・本格焼酎（新蒸留所やワイナリー、国際的な受賞、輸出、新しいスタイル）"
"業界と制度（GI 地理的表示、酒税改正、ユネスコ無形文化遺産『伝統的酒造り』、インバウンド免税、後継者問題、輸出統計）と、秋田県の酒蔵・ワイナリー・ブルワリーの動き"
)
if [ "${SKIP_COLLECT:-0}" != "1" ]; then
for W in "${WINDOWS[@]}"; do read -r U D <<< "$W"
  for T in "${THEMES[@]}"; do
    $PY -u collect/grok_news.py --until "$U" --days "$D" --n 15 --theme "$T" >> "$LOG" 2>&1
    echo "$(date '+%H:%M') collected (until $U): $(wc -l < data/backlog.jsonl) rows" | tee -a "$LOG"
  done
done
fi
echo "CANDIDATES: $($PY -c "import sys;sys.path.insert(0,'write');import pick;print(len(pick.ranked()))" 2>>"$LOG")" | tee -a "$LOG"
N=${N_ARTICLES:-${1:-30}}
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
