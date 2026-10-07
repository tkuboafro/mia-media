# MIA メディア（The Sake Wire）HANDOFF

最終更新: 2026-10-07（PL セッション）。久保さんへの確認は必ず Otacon 経由（~/work/Python/CLAUDE.md「指示系統」）。

## 現在の運用
- 記事: 毎朝 05:30 `run_daily.sh` が1本書く → Notion「確認待ち」＋ Slack レビュー依頼。量産（`batch_past.sh`）は久保さんの指示があるときだけ（`MIA_DEADLINE` で締切指定可）。
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
- Unsplash 本番申請: 申請用記事「湖の誉」公開済み（/en/2026-09-28-shiga-yamaoka-shuzo-revival-ko-no-homare-junmai-ginjo/）。スクショ・フォーム記入 → 久保さん送信待ち。
- 確認待ちの下書き 約300本（Notion）。
