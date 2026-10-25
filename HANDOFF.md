# MIA メディア（The Sake Wire）HANDOFF

最終更新: 2026-10-07（PL セッション）。

## 2026-10-10 再開: 久保さんの直接指示で毎朝の記事作成（com.danshiko.mia-journal）を enable＋bootstrap。量産はまだ（指示待ち）。

## 🟡 保留中（2026-10-07 久保さん指示・Otacon 経由）→ 10/10 に記事作成は再開
「MIA の件は来週火曜の前にトークンが余ったら一気にやるので、置いておいていい」→ **10/13（火）の前まで保留**。
- 新しい作業・上申はしない。久保さんへの確認も出さない（必要なものはこの HANDOFF に溜める）。再開は久保さんが声をかけたとき。
- 毎朝の記事作成 `com.danshiko.mia-journal` は Otacon が bootout＋disable 済み。再開時に bootstrap/enable が必要。
- 承認の見張り `com.danshiko.mia-journal-approve` は稼働のまま（承認が無ければ何もしない）。
- Unsplash「Apply for production」の #cockpit 依頼は閉じた（申請ページ・常駐ブラウザ tab18 はそのまま）。再開時にもう一度 Otacon から出す。

### 再開時に久保さんへ出すもの（溜め）
1. Unsplash の「Apply for production」を押してもらう（準備済み）。
2. 確認待ちの下書き 約300本のレビュー。
久保さんへの確認は必ず Otacon 経由（~/work/Python/CLAUDE.md「指示系統」）。

## 現在の運用
- 記事: 毎朝 05:30 `run_daily.sh` が1本書く（10/7〜10/9 停止、10/10 再開） → Notion「確認待ち」＋ Slack レビュー依頼。量産（`batch_past.sh`）は久保さんの指示があるときだけ（`MIA_DEADLINE` で締切指定可）。
- 公開: `sns/approve_watch.py`（launchd 15分毎）が Notion「承認」を拾い `publish.py` で翻訳→ビルド→push。
  - Slack スレッド巡回は1回40本まで（429 対策, 2026-10-07）。
  - Notion 読み戻し時に画像クレジット（Unsplash リンク等）を元原稿から復元。
  - トップ画像キャプションも各言語に翻訳（`hero_alt`）。以前は全言語に日本語が出ていた。

## SNS（2026-10-07 すべて停止）
- `approve_watch.py`: `X_POST_ENABLED` / `IG_POST_ENABLED` / `THREADS_POST_ENABLED` = False。
  - X: 久保さん「いったん不要」。IG・Threads: 久保さんがアカウントを削除。
- launchd `com.danshiko.mia-ig-refresh` / `com.danshiko.mia-threads-refresh` は bootout＋disable（plist・スクリプトは残置）。
- 再開は久保さんの指示が出てから（Otacon 経由）。

## 画像の方針
- AI 生成は停止（`write/genimg.py` は `MIA_ALLOW_GEN=1` のときだけ）。2026-10-06 久保さんが 369 枚を見て「全般に品質が悪い」。
- 使うのは 引用（プレス・公式SNS・YouTube）→ フリー素材（Pexels / Unsplash / Pixabay / Openverse 経由の Flickr・Wikimedia）。無ければ画像なし。
- 有料ストックは契約しない（2026-10-07 回答 C）。
- 検品（Opus）: 実写はラベル・銘柄名が読めても可（別の蔵の銘柄は NG）。AI っぽい画像は NG。
- Unsplash: 規約対応済み（download_location 通知、撮影者＋Unsplash リンク付きクレジット）。本番申請は久保さん本人が送信。

## 未完了
- Unsplash 本番申請: 2026-10-07 フォーム準備完了（スクショ添付済み・常駐ブラウザ tab18）。久保さんが「Apply for production」を押す待ち（Otacon に連絡済み）。通ったら 50→1,000 回/時。
- 公開まわりの修正（2026-10-07）: publish.py の run() が cwd 二重指定で毎回落ちていた／approve_watch が Slack 429 で落ちていた → どちらも修正、湖の誉で公開確認済み。
- 確認待ちの下書き 約300本（Notion）。

## 2026-10-10〜12 の作業記録
- sakewire フォント G（英語 Fraunces＋Source Serif 4／日本語 Noto Sans JP）公開。OGP 既定画像も同じ書体で作り直し（2026-10-12）。
- ストック全153件を量産（10/10, 160本）。確認待ちは約470本。
- 画像点検ツール `write/audit_media.py`、穴埋め `write/fill_gaps.py`（引用→Opus検品フリー素材、AI生成なし、`FILL_RETRY=1` で一般的な被写体で再挑戦、Notion 手直しページはスキップ）。
- Shopify: About ページを新セクション `mia-about` で作り直し → 下書きテーマ「Horizon v5 (about page)」191919096132（**久保さんが公開待ち**）。推測URLの404に301リダイレクト23件追加（/collections/beer→craft-beer ほか、2026-10-12）。
- レビュー指摘の確認: Privacy の "Poricy" はショップ・ブランドサイトどちらにも無し（誤指摘）。フッターの「Locations: Shibuya · Fukuoka · Amsterdam」はショップのテーマに実在（ワイヤー由来）→ 正しいかは久保さん判断。
- 画像の穴埋め完了（2026-10-14 09:00）: 確認待ち469本で トップ画像なし 122→77本、画像のない見出し 424→226か所 / 1,396。AI画像0・リンク切れ0。10/12 の初回は使用上限で2回とも途中停止 → 10/14 に再開して完走。

## SNS 計画 v3（2026-10-20）
- 本文: docs/sns_ops_v3.md ／ Claude Doc https://claude.ai/code/artifact/0a7a6d26-dad8-4611-8a54-af9ca526716e
- 久保さんの回答待ち（Otacon が #cockpit に出した 7 問）: B1 X API クレジット購入（今は 402 credits depleted で投稿も計測も不可）／B2 IG @thesakewire 存続 or 再作成・@made_in_akita の Meta 接続／C1 MIA の X → **運用しない（10/20 久保さん直接決定）**／C2 MIA 開始 11/2 週・リール→カルーセル／C3 Sake Wire は記事承認＝投稿承認／C4 金曜の「今週の3本」／C5 岩田さんの役割。
- 回答後の実装順: make_cards.py（HTML→PNG テンプレ2種）→ sw_social.py → scheduler.py＋guard.py → mia_social.py（41本を再日付）→ kpi.py。
- 2026-10-20 追記: 投稿は Buffer 経由を提案中（X API クレジット不要・IG トークン管理不要・Buffer API の createPost で予約）。MIA の X なし → チャネルは3つ（Sake Wire の X・IG、MIA の IG）で Buffer 無料プランから試せる。
- 2026-10-21: 久保さん回答（#cockpit「MIA｜岩田さんの役割」）「このプロジェクト俺関係ないから追いかけなくていいです」→ MIA の上申・確認は久保さんに上げない。SNS v3 の上申（B1 X クレジット／B2 IG アカウント／C2 開始日・リール／C3 承認方式／C4 今週の3本／C5 岩田さんの役割）は取り下げ。判断は MIA 側の当事者（岩田さん）と決める。久保さんがこのセッションで直接指示した場合はそれに従う。
- 2026-10-21: 久保さん回答（C2）「A よい」→ MIA の IG は 11/2 の週に開始、リールはカルーセルで代替（実写が撮れた週から戻す）。再日付済みカレンダー: docs/mia_calendar_v3.md／data/sns/mia_calendar_v3.json（IG 30 本、11/3〜2027-01-09）。投稿の手段（Buffer か直接 API か）と @made_in_akita の接続は未決で、決まるまで投稿は始められない。
- 2026-10-21: C3 回答「B」→ Sake Wire の X・IG は投稿ごとに承認（記事承認＝投稿承認の案は不採用）。投稿ページは Notion に「確認待ち」で作り、承認済みだけをスロットに乗せる。N 柱は3日未承認で見送り。承認者は MIA 側で決める（久保さんに上げない）。
- 2026-10-21: C4 回答「A」→ Sake Wire に金曜「今週の3本」を入れる（週1まで）。以後の SNS 運用判断は MIA 側で決める（10/21 久保さん「MIA は追いかけなくていい」）。残る未決: 投稿手段（Buffer か直接 API か）・IG アカウントの接続・承認者（いずれも MIA 側）。
- 2026-10-21: B1 回答「B　Buffer を使うで着地したはず」→ X API クレジットは買わず、投稿は Buffer 経由で確定。scheduler は Buffer API（createPost＋dueAt）に予約を入れる形で作る。久保さん本人の操作（Buffer アカウント・3チャネル接続・API キー）だけ Otacon 経由で1問。MIA の X は運用しない（10/20 決定）。
- 2026-10-21: IG @thesakewire は「A 今のアカウントを残して使う」（10/7 の削除扱いは取り消し、投稿0から運用）。Buffer に接続する。久保さん本人の Buffer 準備（アカウント・3チャネル接続・API キー）は Otacon に1問で確認中。
- 2026-10-21: Buffer 準備完了（久保さん）。API キーは Secret Manager danshikolab/buffer-api-key → secrets.env の BUFFER_API_KEY に取り込み済み。3チャネル接続を API で確認（sns/buffer_channels.json に組織・チャネル ID）。次は実装: make_cards.py → sw_social.py → buffer_client.py＋scheduler.py＋guard.py → mia_social.py（11/3 初回）→ kpi.py。新しいセッションで HANDOFF を読んでから着手するのが安い。
- 2026-10-21: 投稿の承認は Notion「MIA SNS投稿管理」だけで回す（#cockpit・Asana は使わない、久保さん決定）。流れ: PL が1投稿1行で起票→「確認待ち」→ 久保さんが「承認」/「差戻し」（理由は「承認コメント」）→ PL は「承認」だけ Buffer に予約して「予約済み」・「Buffer ID」記入 → 投稿後「投稿済み」＋「投稿URL」。差戻しは直して「確認待ち」へ。列「アカウント」（X @TheSakeWire／IG @thesakewire／IG @made_in_akita）と「Buffer ID」を追加。ビュー「SNS 確認待ち（日付順）」= https://app.notion.com/p/fdf23074b8164aa0978c880785f3238c?v=3ff3f775adf481e191a1000c430032c2 （記事レビューの Journal 行は除外）。既存の行・ビュー・列・ページ本文は触らない。久保さんへの連絡は、投稿予定日の前日までに「確認待ち」が残っているときだけ Otacon に1行。
- 2026-10-25: Notion DB に列「IGキャプション」「X投稿文（Threads共用）」を追加。MIA の IG 30本を起票（ステータス 制作中・キャプション入り・画像は未作成）。記事 479本分の投稿文は `sns/sns_texts.py`（6本ずつ Sonnet、再開可）で作るが、**この Mac の claude CLI の OAuth が切れていて未実行**。同じ原因で毎朝の記事作成も 10/23 から失敗中。久保さんが `claude` → `/login` で再ログインしたら `python3 sns/sns_texts.py` を回す。
- 2026-10-25: claude CLI 再ログイン済み（久保さん）。記事 479本すべてに「IGキャプション」「X投稿文（Threads共用）」を作成して Notion に記入（原稿 JSON の meta['sns'] にも保存）。毎朝の記事作成も復旧。IG @thesakewire のプロフィール（名前・自己紹介・リンク・カテゴリ・最低年齢18）は API で変えられないので、文面を久保さんに渡してアプリで設定してもらう。
