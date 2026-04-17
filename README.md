# bull

GitHub Actions で毎朝 7 時に PDF の給食献立表から当日の献立を抽出し、LINE に通知する仕組みです。

LINE への通知は、LINE公式アカウントを友だち追加している相手全員へのブロードキャスト配信です。

毎月の PDF は、このリポジトリの `menus/latest.pdf` に置いて運用します。

## 構成

- `.github/workflows/notify-daily-menu.yml`
  - 毎日 7:00 JST (`22:00 UTC`) に実行
  - 手動実行 (`workflow_dispatch`) にも対応
- `scripts/notify_daily_menu.py`
  - 保存済み PDF を優先して読み込み
  - 必要なら URL から PDF を取得
  - テキストを抽出
  - 当日の日付に対応する行を見つけて献立を組み立て
  - LINE Messaging API で通知
- `tests/test_notify_daily_menu.py`
  - 日付抽出と通知整形の最小テスト

## 事前準備

### 1. LINE Messaging API の設定

LINE Notify は終了済みのため、LINE Messaging API を使います。

以下を用意して GitHub Secrets に登録してください。

- `LINE_CHANNEL_ACCESS_TOKEN`
  - Messaging API のチャネルアクセストークン

通常運用で PDF をリポジトリに置く場合、`MENU_PDF_URL` は不要です。

必要なら、手動実行や一時検証用に次も使えます。

- `MENU_PDF_URL`
  - 月次献立 PDF の URL

`LINE_TO` は不要です。この実装は Push Message ではなく Broadcast API を使って、友だち追加済みの相手全員に配信します。

必要に応じて以下も設定できます。

- `MENU_TIMEZONE`
  - 既定値: `Asia/Tokyo`
- `MENU_PDF_PATH`
  - 既定値: `menus/latest.pdf`

## 月次 PDF の更新方法

1. コドモンから月次の献立 PDF をダウンロードする
2. このリポジトリの `menus/latest.pdf` をその PDF で置き換える
3. GitHub にコミットして push する
4. 翌朝の GitHub Actions がその PDF を読み、当日の献立を配信する

月ごとに履歴を残したい場合は、`menus/2026-04.pdf` のような名前でも保存し、運用上の最新だけを `menus/latest.pdf` にコピーしておくと分かりやすいです。

## 手動実行

Actions の `Notify Daily Menu` ワークフローから手動実行できます。

- `menu_date`
  - `YYYY-MM-DD` 形式で対象日を指定
- `menu_pdf_url`
  - 保存済み PDF を使わず、一時的に別 PDF を試したい場合に指定

## PDF 形式の前提

この実装は、PDF からテキスト抽出できることを前提にしています。

- `4/15`
- `04/15`
- `4月15日`
- `15(水)`
- `15日（水）`

のような日付表記を含む行を探し、その行または直後の数行を当日の献立として通知します。

画像だけのスキャン PDF や、表のレイアウトによっては OCR や個別調整が必要です。

## 通知内容

毎朝 7:00 JST に、`menus/latest.pdf` の中から当日分だけを抽出し、全友だちへ次のような見やすい形式で送信します。

```text
【今日の給食】2026-04-15（水）
・ごはん
・鶏の唐揚げ
・味噌汁
```

## ローカル確認

```bash
python -m unittest discover -s tests
```
