# MADE IN AKITA Journal — automated multilingual media

Daily pipeline (Mac mini, launchd 05:30 Europe/Amsterdam):
1. `collect/grok_news.py` — Japanese alcohol news via grok.com screen (resident browser). Falls back to `collect/claude_news.py` (Claude WebSearch) when Grok is capped.
2. `write/select.py` — pick today's story (Akita weighted).
3. `write/article.py` — EN/NL/DE/ES articles via `claude -p` → `site/src/content/articles/<lang>/<slug>.md`.
4. `site/` (Astro) build check.
5. `sns/derive.py` — Instagram carousel + X drafts → `sns_queue/`.
6. PR `article/<slug>` — **merge = approve & publish** (GitHub Pages deploys `main`). Close = skip.

Secrets (optional, `~/mia-media/secrets.env`, chmod 600): `SLACK_BOT_TOKEN`, `SLACK_APPROVER_ID`, `NOTION_TOKEN`, `FAL_KEY`.
