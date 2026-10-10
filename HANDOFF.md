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
