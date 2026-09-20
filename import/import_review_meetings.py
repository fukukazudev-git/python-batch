"""CSV から検証会（review meeting）を一括登録するインポートバッチ。

使い方:
    python import/import_review_meetings.py <csvファイルパス>

処理概要:
    CSV を読み込み、ヘッダーの表記ゆれを内部名に正規化し、デフォルト値を補完、
    バリデーション（全件）を行ってからログインして 1 件ずつ API に登録する。
    バリデーションでエラーがある場合は 1 件も登録しない。
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

# 直接実行するスクリプトなので、リポジトリルートを import パスに追加して
# 共通モジュール（config / api_client）を読み込めるようにする。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from api_client import (  # noqa: E402
    create_review_meeting,
    get_models,
    get_users,
    login,
)

# 表記ゆれ（別名）→ 内部名 の逆引き辞書を 1 度だけ構築する。
_ALIAS_TO_INTERNAL: dict[str, str] = {
    alias: internal for internal, aliases in config.COLUMN_MAPPING.items() for alias in aliases
}

# 非空チェックの対象（notes 以外の全内部カラム）。
_REQUIRED_NON_EMPTY: list[str] = [c for c in config.COLUMN_MAPPING if c != "notes"]


def normalize_headers(row: dict) -> dict:
    """CSV 1 行分の列名を COLUMN_MAPPING に基づいて内部名へ正規化して返す。

    Args:
        row: csv.DictReader が返す 1 行（列名 -> 値）。

    Returns:
        列名を内部名に変換した辞書。マッピングに無い列名はそのまま残す。
        値の前後空白は除去する。
    """
    normalized: dict = {}
    for key, value in row.items():
        if key is None:
            # 列数より値が多い場合に DictReader が None キーへ詰めるため無視する。
            continue
        internal = _ALIAS_TO_INTERNAL.get(key.strip(), key.strip())
        # strip()が文字列専用のメソッドなので、値が文字列の場合のみ適用する。
        normalized[internal] = value.strip() if isinstance(value, str) else value
    return normalized


def apply_defaults(row: dict) -> dict:
    """COLUMN_DEFAULTS を使って欠損・空カラムを補完した行を返す。

    Args:
        row: 正規化済みの 1 行。

    Returns:
        デフォルト値を補完した行（入力を破壊しない新しい辞書）。
    """
    filled = dict(row)
    for key, default in config.COLUMN_DEFAULTS.items():
        if not filled.get(key):
            filled[key] = default
    return filled


def validate(row: dict) -> list[str]:
    """1 行分のバリデーションを行い、エラーメッセージのリストを返す。

    検証内容:
        a. 必須フィールド（notes 以外）が空でないこと
        b. scheduled_date が YYYY-MM-DD 形式であること
        c. status が VALID_STATUSES のいずれかであること

    Args:
        row: デフォルト補完済みの 1 行。

    Returns:
        エラーメッセージのリスト（エラーが無ければ空リスト）。
    """
    errors: list[str] = []

    # a. 必須フィールドの非空チェック
    for field in _REQUIRED_NON_EMPTY:
        if not str(row.get(field, "")).strip():
            errors.append(f"必須項目 '{field}' が空です")

    # b. 日付形式チェック
    scheduled_date = str(row.get("scheduled_date", "")).strip()
    if scheduled_date:
        try:
            # バリデーションのため戻り値は変数に受けず捨てる
            datetime.strptime(scheduled_date, config.DATE_FORMAT)
        except ValueError:
            errors.append(f"scheduled_date '{scheduled_date}' が日付形式(YYYY-MM-DD)ではありません")

    # c. ステータス語彙チェック
    status = str(row.get("status", "")).strip()
    if status and status not in config.VALID_STATUSES:
        allowed = "/ ".join(config.VALID_STATUSES)
        errors.append(f"status '{status}' が不正です（許可値: {allowed}）")

    return errors


def _print_usage() -> None:
    """コマンドラインの使い方を表示する。"""
    print("使い方: python import/import_review_meetings.py <csvファイルパス>")


def _load_rows(csv_path: Path) -> tuple[list[str], list[dict]]:
    """CSV を UTF-8 で読み込み、(元ヘッダー, 正規化済み行リスト) を返す。"""
    # ブロック内で例外が発生してもwithで必ず閉じる
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = [normalize_headers(row) for row in reader]
    return list(fieldnames), rows


def _check_required_headers(fieldnames: list[str]) -> list[str]:
    """ヘッダーに必須カラム（内部名）が揃っているか確認し、不足分を返す。"""
    present = {_ALIAS_TO_INTERNAL.get(name.strip(), name.strip()) for name in fieldnames}
    return [col for col in config.REQUIRED_COLUMNS if col not in present]


def _validate_all(rows: list[dict]) -> list[str]:
    """全行のバリデーション（行単位 + CSV 内の title 重複）を行いエラーを返す。

    行番号はヘッダーを 1 行目としたファイル上の行番号（最初のデータ行 = 2）。
    """
    errors: list[str] = []

    for index, row in enumerate(rows, start=2):
        for message in validate(row):
            errors.append(f"{index}行目: {message}")

    # d. 同一 CSV 内での title 重複チェック
    title_lines: dict[str, list[int]] = {}
    for index, row in enumerate(rows, start=2):
        title = str(row.get("title", "")).strip()
        if title:
            title_lines.setdefault(title, []).append(index)
    for title, lines in title_lines.items():
        if len(lines) > 1:
            joined = ", ".join(str(n) for n in lines)
            errors.append(f"title '{title}' が重複しています（{joined}行目）")

    return errors


def _build_payload(row: dict, model_id: int, organizer_id: int) -> dict:
    """API 登録用の payload を組み立てる。notes が空文字なら None にする。"""
    notes = str(row.get("notes", "")).strip()
    return {
        "modelId": model_id,
        "organizerId": organizer_id,
        "title": row["title"].strip(),
        "scheduledDate": row["scheduled_date"].strip(),
        "status": row["status"].strip(),
        "eventCode": row["event_code"].strip(),
        "notes": notes or None,
    }


def main(argv: list[str]) -> int:
    """エントリポイント。終了コードを返す（0=正常, 1=異常）。"""
    # ① 引数チェック
    if len(argv) != 2:
        _print_usage()
        return 1

    csv_path = Path(argv[1])
    if not csv_path.is_file():
        print(f"CSVファイルが見つかりません: {csv_path}")
        return 1

    # ②③ 読み込み + ヘッダー正規化
    try:
        fieldnames, raw_rows = _load_rows(csv_path)
    except UnicodeDecodeError:
        print("CSVの文字コードが UTF-8 ではありません。UTF-8 で保存してください。")
        return 1
    except OSError as e:
        print(f"CSVの読み込みに失敗しました: {e}")
        return 1

    # ③ 必須カラム（ヘッダー）の存在チェック
    missing = _check_required_headers(fieldnames)
    if missing:
        print("CSVに必須カラムが不足しています: " + ", ".join(missing))
        return 1

    if not raw_rows:
        print("CSVにデータ行がありません。")
        return 1

    # ④ デフォルト値補完
    rows = [apply_defaults(row) for row in raw_rows]

    # ⑤ バリデーション（エラーがあれば全件表示して終了）
    errors = _validate_all(rows)
    if errors:
        print(f"バリデーションエラーが {len(errors)} 件あります。登録は行いません。")
        for message in errors:
            print(f"  - {message}")
        return 1

    # ⑥ ログイン
    try:
        token = login(config.LOGIN_USERNAME, config.LOGIN_PASSWORD)
    except RuntimeError as e:
        print(e)
        return 1

    # ⑦ ユーザー・モデル一覧を取得してキャッシュ（行ごとに API を叩かない）
    try:
        users_map = {user["username"]: user["id"] for user in get_users(token)}
        models_map = {model["modelCode"]: model["id"] for model in get_models(token)}
    except RuntimeError as e:
        print(e)
        return 1
    except KeyError as e:
        print(f"APIレスポンス形式が想定と異なります: {e}")
        return 1

    # ⑧ 各行を登録
    success_count = 0
    failures: list[str] = []
    for index, row in enumerate(rows, start=2):
        model_code = row["model_code"].strip()
        model_id = models_map.get(model_code)
        if model_id is None:
            failures.append(f"{index}行目: 機種コード '{model_code}' がマスタに存在しません")
            continue

        organizer_username = row["organizer_username"].strip()
        organizer_id = users_map.get(organizer_username)
        if organizer_id is None:
            failures.append(f"{index}行目: 担当者 '{organizer_username}' がマスタに存在しません")
            continue

        payload = _build_payload(row, model_id, organizer_id)
        try:
            create_review_meeting(token, payload)
            success_count += 1
        except RuntimeError as e:
            failures.append(f"{index}行目: 登録に失敗しました ({e})")

    # ⑨ 結果レポート
    print("=" * 40)
    print("インポート結果")
    print(f"  成功: {success_count} 件")
    print(f"  失敗: {len(failures)} 件")
    if failures:
        print("失敗した行:")
        for message in failures:
            print(f"  - {message}")
    print("=" * 40)

    return 0 if not failures else 1


if __name__ == "__main__":
    # sys.exit()に終了コードを渡し、プロセスの終了コードとする
    sys.exit(main(sys.argv))
