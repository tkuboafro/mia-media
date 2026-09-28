#!/bin/bash
# 久保さん 2026-09-28「追加収集して最大100記事」: ①現行バッチの収集完了を待つ → ②4〜6月分を追加収集（現行の執筆と並走）→ ③現行30本の後に残り70本を執筆
set -u; export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
H="$HOME/mia-media"; cd "$H"; L1=$(ls -t logs/batch_past_*.log | head -1); OUT="$H/logs/run_to_100.log"
echo "$(date '+%F %T') waiting for collection phase of $L1" >> "$OUT"
until grep -q "CANDIDATES" "$L1"; do sleep 60; done
echo "$(date '+%F %T') extra collection Apr-Jun" >> "$OUT"
MIA_WINDOWS='"2026-04-30 30" "2026-05-31 31" "2026-06-30 30"' SKIP_WRITE=1 bash -c '
  export MIA_MAX_AGE_DAYS=200; H="$HOME/mia-media"; PY=/usr/bin/python3; LOG="$H/logs/batch_more_$(date +%F_%H%M).log"; cd "$H"
  eval "WINDOWS=($MIA_WINDOWS)"
  THEMES=(
  "国際コンクールの受賞（IWC・Kura Master・SAKE COMPETITION・Milano Sake Challenge・IWSC・ISC・全国新酒鑑評会・ワインコンクール）と、日本酒・焼酎・ウイスキー・日本ワインの輸出・海外展開"
  "蔵元の物語（代替わり・若手や女性の杜氏・新しい蔵の開業・休止や廃業からの復活・異業種や海外出身の醸造家）と、造りの技術・研究（酵母や酒米、低アル・スパークリング・熟成・木桶・生酛、クラフトサケ、大学との共同研究）"
  "ジャパニーズウイスキー・クラフトジン・日本ワイン・クラフトビール・本格焼酎（新蒸留所やワイナリー、国際的な受賞、輸出、新しいスタイル）"
  "業界と制度（GI 地理的表示、酒税、ユネスコ無形文化遺産『伝統的酒造り』、インバウンド免税、後継者問題、輸出統計、海外の日本酒ブーム）と、秋田県の酒蔵・ワイナリー・ブルワリーの動き"
  )
  for W in "${WINDOWS[@]}"; do set -- $W; U=$1; D=$2
    for T in "${THEMES[@]}"; do
      $PY -u collect/grok_news.py --until "$U" --days "$D" --n 15 --theme "$T" >> "$LOG" 2>&1
      echo "$(date "+%H:%M") collected (until $U): $(wc -l < data/backlog.jsonl) rows" | tee -a "$LOG" >> "$HOME/mia-media/logs/run_to_100.log"
    done
  done'
echo "$(date '+%F %T') waiting for first 30 to finish" >> "$OUT"
until grep -q "batch_past done" "$L1"; do sleep 60; done
W1=$(grep -c "WROTE" "$L1"); REST=$((100 - W1)); echo "$(date '+%F %T') first batch wrote $W1; writing up to $REST more" >> "$OUT"
MIA_MAX_AGE_DAYS=200 SKIP_COLLECT=1 bash batch_past.sh "$REST"
echo "$(date '+%F %T') ALL DONE" >> "$OUT"
