import os

# .env を読み込む（ローカル実行向け。CI/本番は実環境変数をそのまま使う）。
# python-dotenv 未導入でも実環境変数だけで動作するよう、import 失敗は無視する。
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# API 接続先。環境（ローカル/ステージング/本番）で切り替える。
# URL は秘密情報ではないため、ローカル開発向けの既定値のみ持つ。
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")

# 検証会管理 API を呼び出すバッチ専用アカウントの資格情報の環境変数名。
# 秘密情報のため既定値は持たず、実行時に get_credentials() で必須チェックする。
# ローカル開発では API の初期管理者 (ADMIN_USERNAME/ADMIN_PASSWORD, 既定 admin/admin)
# に合わせた値を .env / 環境変数に設定する。
ENV_USERNAME = "BATCH_API_USERNAME"
ENV_PASSWORD = "BATCH_API_PASSWORD"


def get_credentials() -> tuple[str, str]:
    """バッチ専用アカウントの (username, password) を環境変数から取得する。

    秘密情報のため既定値は持たない。いずれかが未設定・空なら RuntimeError を送出する
    （誤った既定値で本番 API にログインを試み、アカウントをロックさせる事故を防ぐため）。
    """
    username = os.environ.get(ENV_USERNAME)
    password = os.environ.get(ENV_PASSWORD)
    missing = [
        name for name, value in ((ENV_USERNAME, username), (ENV_PASSWORD, password)) if not value
    ]
    if missing:
        raise RuntimeError(
            "資格情報の環境変数が未設定です: "
            + ", ".join(missing)
            + "。.env または環境変数に設定してください。"
        )
    return username, password


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
