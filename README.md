# Vehicle Verification Python Batch

## 概要
Vehicle Verification API と連携する Python バッチツール群です。
既存の検証会日程管理 Excel や SharePoint からエクスポートした CSV を対象に、
検証会の一括登録（インポート）と、検証会一覧の CSV/Excel 出力（エクスポート）を行います。
（実行頻度は低い運用を想定）

## セットアップ
```
pip install -r requirements.txt
```
Python 3.11 以上を想定。

## 開発（任意）
仮想環境（venv）と ruff（リンタ＋フォーマッタ）を推奨します。

```powershell
# 仮想環境の作成・有効化（PowerShell）
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
# 有効化がブロックされる場合: Set-ExecutionPolicy -Scope Process RemoteSigned

# 開発用依存（ruff 含む）をインストール
pip install -r requirements-dev.txt
```

```
# 整形とチェック
ruff format .
ruff check . --fix
```

## ディレクトリ構成
```
python-batch/
├── config.py          共通設定
├── api_client.py      API呼び出し（共通）
├── requirements.txt
├── import/
│   ├── import_review_meetings.py
│   └── sample.csv
└── export/
    └── export_review_meetings.py
```

## インポートバッチ（CSVから検証会を一括登録）
```
python import/import_review_meetings.py <csvファイルパス>
```

### CSVフォーマット
| カラム | 必須 | 説明 | 列名の揺れ例 |
|---|---|---|---|
| model_code | ✅ | 機種コード | 機種コード, ModelCode |
| title | ✅ | 検証会タイトル | タイトル, 検証会名 |
| scheduled_date | ✅ | 日付（YYYY-MM-DD） | 日程, 実施日 |
| organizer_username | ✅ | 担当者username | 担当者, 主催者 |
| status | ❌ | 検証前・検証中・完了・中断 | ステータス, 状態 |
| event_code | ❌ | イベント番号 | イベント |
| notes | ❌ | 備考（自由記述） | 備考, メモ |

欠損カラムのデフォルト値:
- status: 検証前
- event_code: 未設定
- notes: （空）

### 実行例
```
python import/import_review_meetings.py import/sample.csv
```

## エクスポートバッチ（検証会一覧をCSV/Excelで出力）
```
python export/export_review_meetings.py --format [csv|excel] --output <出力ファイルパス>
```

出力カラム: 機種コード / 機種名 / 検証会タイトル / イベントコード / 実施予定日 /
ステータス / 担当者名 / テスト総数 / OK数 / NG数 / 保留数 / OK率 / 備考(notes)

### 実行例
```
# CSV出力（Excelでの文字化け防止のため UTF-8-sig で書き込み）
python export/export_review_meetings.py --format csv --output output.csv

# Excel出力
python export/export_review_meetings.py --format excel --output output.xlsx
```

## 拡張案
S3 に CSV をアップロードして Lambda で自動処理する構成への拡張も可能です。
アップロードイベントをトリガーに Lambda（Python）を起動し、
バリデーション後に Spring API へ登録する構成が考えられます。
