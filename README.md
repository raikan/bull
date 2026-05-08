# bull

GitHub Actions から LINE に通知する小さな自動化置き場です。

現状は次の 2 つに対応しています。

- 給食献立 PDF から当日メニューを抽出して通知
- JR北海道 学園都市線の遅延・運休情報を監視して通知

LINE への通知は、LINE公式アカウントを友だち追加している相手全員へのブロードキャスト配信です。

毎月の PDF は、このリポジトリの `menus/latest.pdf` に置いて運用します。

## 構成

- `.github/workflows/notify-daily-menu.yml`
  - 毎日 6:30 JST (`21:30 UTC`) に実行
  - 手動実行 (`workflow_dispatch`) にも対応
- `.github/workflows/notify-train-delay.yml`
  - 10分ごとに実行
  - 遅延・運休などが検知されたときだけ LINE に通知
  - 前回と同じ障害内容は再通知しない
- `scripts/notify_daily_menu.py`
  - 保存済み PDF を優先して読み込み
  - 必要なら URL から PDF を取得
  - テキストを抽出
  - 当日の日付に対応する行を見つけて献立を組み立て
  - LINE Messaging API で通知
- `scripts/notify_train_delay.py`
  - 運行情報ページを取得
  - 学園都市線/札沼線に関する文言を抽出
  - 遅延・運休・運転見合わせなどを検知
  - 同じ内容の重複通知を抑止
- `tests/test_notify_daily_menu.py`
  - 日付抽出と通知整形の最小テスト
- `tests/test_notify_train_delay.py`
  - 運行情報の判定と重複通知抑止のテスト

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

### 2. JR北海道 遅延通知の設定

学園都市線の遅延通知でも同じ `LINE_CHANNEL_ACCESS_TOKEN` を使います。

必要に応じて GitHub Secrets で次を設定できます。

- `TRAIN_STATUS_URLS`
  - 運行情報ページの URL 一覧
  - 改行またはカンマ区切り
  - 未設定時は以下を順に参照
    - `https://www3.jrhokkaido.co.jp/webunkou/`
    - `https://transit.yahoo.co.jp/diainfo/12/0`
- `TRAIN_STATUS_TIMEZONE`
  - 既定値: `Asia/Tokyo`
- `TRAIN_LINE_NAME`
  - 通知見出しに出す路線名
  - 既定値: `学園都市線`
- `TRAIN_LINE_ALIASES`
  - ページ上で検索する路線名候補
  - 既定値: `学園都市線,札沼線`
- `TRAIN_COMMUTE_SECTION`
  - 通知見出しに付ける区間名
  - 既定値: `拓北〜札幌`

同じ遅延内容が継続している間は、GitHub Actions の cache に前回状態を保存して重複通知を避けます。

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

`Notify Train Delay` ワークフローも手動実行できます。

- `force_notify`
  - `true` にすると、前回と同じ障害内容でも通知
- `status_urls`
  - 一時的に参照先 URL を差し替えたいときに指定

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

毎朝 6:30 JST 頃に、`menus/latest.pdf` の中から当日分だけを抽出し、全友だちへ次のような見やすい形式で送信します。

```text
【今日の給食】2026-04-15（水）
・ごはん
・鶏の唐揚げ
・味噌汁
```

日曜日や休園日などで当日の献立が PDF に見つからない場合は、LINE は送信せず、その日の workflow は正常終了します。

学園都市線で遅延や運休が検知された場合は、次のような形式で送信します。

```text
【JR北海道 運行情報】学園都市線（拓北〜札幌）
学園都市線は強風の影響で遅れが発生しています。
確認時刻: 2026-05-08 08:10
取得元: https://www3.jrhokkaido.co.jp/webunkou/
```

## ローカル確認

```bash
python -m unittest discover -s tests
```
