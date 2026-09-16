#!/bin/bash
# MADE IN AKITA Journal — 日次パイプライン（launchd から 05:30 現地で起動）。
#   収集(Grok画面 → だめなら Claude WebSearch) → 選定 → 4言語執筆 → ビルド確認 → PR 作成（久保さんがマージ＝承認）→ SNS 下書き
# 罠: launchd は iCloud 配下を読めない・TZ は Amsterdam。ここは ~/mia-media（iCloud 外）に置いてある。
set -u
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
H="$HOME/mia-media"; LOG="$H/logs/daily_$(date +%F).log"; PY=/usr/bin/python3
[ -f "$H/secrets.env" ] && set -a && . "$H/secrets.env" && set +a
cd "$H" || exit 1
echo "=== $(date '+%F %T') start ===" >> "$LOG"
git checkout -q main && git pull -q --ff-only

# ① 収集（Grok 画面のみ。上限なら exit 3 → その日は収集なし。Claude 検索への代替はしない＝久保さん方針 2026-09-16）
$PY -u collect/grok_news.py >> "$LOG" 2>&1
RC=$?
[ "$RC" = "3" ] && echo "grok capped — using backlog only" >> "$LOG"

# ② 選定（バックログから未使用・10日以内の1件。無ければ今日は更新なし）
ROW=$($PY write/pick.py 2>>"$LOG")
if [ -z "$ROW" ] || [ "$ROW" = "null" ]; then echo "no candidate today (backlog empty)" >> "$LOG"; exit 0; fi
echo "$ROW" > data/today.json
$PY -c "import json;json.dump({'rows':[json.load(open('data/today.json'))]},open('data/today_news.json','w'),ensure_ascii=False)"

# ③ 日本語原稿を執筆（正本）
SLUG=$($PY write/article_ja.py data/today_news.json 0 2>>"$LOG" | head -1)
[ -z "$SLUG" ] && { echo "write failed" >> "$LOG"; exit 1; }
echo "$($PY -c "import json;print(json.load(open('data/today.json'))['url'])")" >> data/used_urls.txt

# ④ Notion にページを作り、#biz-mia_media に Otacon からレビュー依頼（承認→翻訳→公開は sns/approve_watch.py）
$PY sns/review_request.py "$SLUG" >> "$LOG" 2>&1
echo "=== $(date '+%F %T') done $SLUG ===" >> "$LOG"
