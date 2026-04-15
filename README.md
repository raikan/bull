# bull

GitHub Actions で毎朝 7 時に PDF の給食献立表から当日の献立を抽出し、LINE に通知する仕組みです。

## 構成

- `.github/workflows/notify-daily-menu.yml`
  - 毎日 7:00 JST (`22:00 UTC`) に実行
  - 手動実行 (`workflow_dispatch`) にも対応
- `scripts/notify_daily_menu.py`
  - PDF を取得
  - テキストを抽出
  - 当日の日付に対応する行を見つけて献立を組み立て
  - LINE Messaging API で通知
- `tests/test_notify_daily_menu.py`
  - 日付行の抽出ロジックの最小テスト

## 事前準備

### 1. LINE Messaging API の設定

LINE Notify は終了済みのため、LINE Messaging API を使います。

以下を用意して GitHub Secrets に登録してください。

- `LINE_CHANNEL_ACCESS_TOKEN`
  - Messaging API のチャネルアクセストークン
- `LINE_TO`
  - Push Message の送信先 ID（ユーザー / グループ / ルーム）
- `MENU_PDF_URL`
  - 月次献立 PDF の URL

必要に応じて以下も設定できます。

- `MENU_TIMEZONE`
  - 既定値: `Asia/Tokyo`

## 手動実行

Actions の `Notify Daily Menu` ワークフローから手動実行できます。

- `menu_date`
  - `YYYY-MM-DD` 形式で対象日を指定
- `menu_pdf_url`
  - 一時的に別 PDF を試したい場合に指定

## PDF 形式の前提

この実装は、PDF からテキスト抽出できることを前提にしています。

- `4/15`
- `04/15`
- `4月15日`
- `15(水)`
- `15日（水）`

のような日付表記を含む行を探し、その行または直後の数行を当日の献立として通知します。

画像だけのスキャン PDF や、表のレイアウトによっては OCR や個別調整が必要です。

## ローカル確認

```bash
python -m unittest discover -s tests
```
