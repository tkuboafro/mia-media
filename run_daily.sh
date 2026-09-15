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

# ① 収集
NEWS=$($PY -u collect/grok_news.py 2>>"$LOG" | tail -1)
KEPT=$($PY -c "import json,sys;print(len(json.load(open(sys.argv[1]))['rows']))" "$NEWS" 2>/dev/null || echo 0)
if [ "${KEPT:-0}" -lt 3 ]; then
  echo "grok kept=$KEPT → claude websearch fallback" >> "$LOG"
  NEWS2=$($PY -u collect/claude_news.py 2>>"$LOG" | tail -1)
  NEWS="$NEWS $NEWS2"
fi

# ② 選定
ROW=$($PY write/select.py $NEWS 2>>"$LOG")
if [ -z "$ROW" ] || [ "$ROW" = "null" ]; then echo "no candidate today" >> "$LOG"; exit 0; fi
echo "$ROW" > data/today.json
$PY -c "import json;json.dump({'rows':[json.load(open('data/today.json'))]},open('data/today_news.json','w'),ensure_ascii=False)"

# ③ 執筆（4言語）
SLUG=$($PY write/article.py data/today_news.json 0 2>>"$LOG" | head -1)
[ -z "$SLUG" ] && { echo "write failed" >> "$LOG"; exit 1; }

# ④ ビルド確認（壊れた記事を PR にしない）
( cd site && npm run build >>"$LOG" 2>&1 ) || { echo "build failed, reverting" >> "$LOG"; git checkout -- site/src/content; exit 1; }

# ⑤ SNS 下書き
$PY sns/derive.py "data/article_$SLUG.json" >> "$LOG" 2>&1

# ⑥ PR（久保さんがマージすると Pages が自動デプロイ）
BR="article/$SLUG"
git checkout -q -b "$BR"
git add site/src/content/articles sns_queue
TITLE_EN=$($PY -c "import re,sys;t=open('site/src/content/articles/en/$SLUG.md').read();print(re.search(r'^title: \"(.*)\"',t,re.M).group(1))")
git commit -q -m "journal: $SLUG" -m "Auto-generated daily story. Merge = approve & publish." 
git push -q -u origin "$BR"
BODY=$($PY - "$SLUG" <<'PYEOF'
import json,re,sys
slug=sys.argv[1]; meta=json.load(open(f"data/article_{slug}.json")); r=meta["row"]
out=[f"**Source:** [{r['title']}]({r['url']}) — {r.get('source','')} ({r.get('published','')})", "", f"**Region:** {r.get('region','')} · **Category:** {r.get('category','')} · **Akita:** {r.get('akita')}", "", "| lang | title | lead |","|---|---|---|"]
for L in ("en","nl","de","es"):
    t=open(f"site/src/content/articles/{L}/{slug}.md").read()
    ti=re.search(r'^title: "(.*)"',t,re.M).group(1); d=re.search(r'^description: "(.*)"',t,re.M).group(1)
    out.append(f"| {L} | {ti} | {d} |")
out += ["", "Merge this PR to publish on all four language sites. Close it to skip the story.", "", f"SNS drafts: `sns_queue/{slug}.json`"]
print("\n".join(out))
PYEOF
)
PR_URL=$(gh pr create --title "Journal: $TITLE_EN" --body "$BODY" --base main --head "$BR" 2>>"$LOG")
echo "PR: $PR_URL" >> "$LOG"
git checkout -q main

# ⑦ 久保さんへ通知（Slack Bot トークンがあれば DM、無ければ GitHub の PR 通知メールに任せる）
if [ -n "${SLACK_BOT_TOKEN:-}" ] && [ -n "${SLACK_APPROVER_ID:-}" ]; then
  curl -s -X POST https://slack.com/api/chat.postMessage -H "Authorization: Bearer $SLACK_BOT_TOKEN" -H 'Content-Type: application/json' \
    -d "$(jq -n --arg ch "$SLACK_APPROVER_ID" --arg t "📰 Journal 本日の記事案: $TITLE_EN
$PR_URL
マージ＝公開（4言語同時）／クローズ＝見送り" '{channel:$ch, text:$t}')" >> "$LOG" 2>&1
fi
echo "=== $(date '+%F %T') done $SLUG ===" >> "$LOG"
