API_BASE_URL = "http://localhost:8080"
LOGIN_USERNAME = "admin"
LOGIN_PASSWORD = "admin"

# インポート用: デフォルトを持たない=真に必須の列だけをヘッダー必須にする
# (status / event_code は COLUMN_DEFAULTS で補完するため、ヘッダー必須にはしない)
REQUIRED_COLUMNS = [
    "model_code",
    "title",
    "scheduled_date",
    "organizer_username",
]

# ステータス語彙(検証前/検証中/…)は Spring の enum を単一の情報源とし、
# import 時に API(GET /api/review-meetings/statuses)から取得する。
# ここでは定数として持たない(二重管理の回避)。
DATE_FORMAT = "%Y-%m-%d"

# ヘッダー名の揺れを吸収するマッピング (内部名: 受理する表記のリスト)
COLUMN_MAPPING = {
    "model_code": ["model_code", "機種コード", "ModelCode"],
    "title": ["title", "タイトル", "検証会名", "会議名"],
    "scheduled_date": ["scheduled_date", "日程", "実施日", "予定日"],
    "status": ["status", "ステータス", "状態"],
    "organizer_username": ["organizer_username", "担当者", "主催者", "organizer"],
    "notes": ["notes", "備考", "メモ"],
    "event_code": ["event_code", "イベント", "イベントコード"],
}

# 欠損カラムのデフォルト値
COLUMN_DEFAULTS = {
    "status": "検証前",
    "notes": "",
    "event_code": "未設定",
}
