"""検証会一覧をテスト結果サマリー付きで CSV / Excel に出力するエクスポートバッチ。

使い方:
    python export/export_review_meetings.py --format [csv|excel] --output <出力ファイルパス>

処理概要:
    ログイン後に検証会一覧を取得し、各検証会のテスト結果サマリーを取得して
    1 行にまとめ、指定形式（CSV は UTF-8-sig / Excel は openpyxl）で出力する。
"""

import argparse
import csv
import sys
from pathlib import Path

# 直接実行するスクリプトなので、リポジトリルートを import パスに追加する。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from api_client import (  # noqa: E402
    get_models,
    get_review_meetings,
    get_test_summary,
    login,
)

# 出力カラム: (ヘッダー表示名, 検証会/サマリーのキー) の順序付き定義。
# 実際の行組み立てはキーに依存せず _build_row で行うため、ここはヘッダー順の定義。
HEADERS: list[str] = [
    "機種コード",
    "機種名",
    "検証会タイトル",
    "イベントコード",
    "実施予定日",
    "ステータス",
    "担当者名",
    "テスト総数",
    "OK数",
    "NG数",
    "保留数",
    "OK率",
    "備考",
]

SHEET_TITLE = "検証会一覧"


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    """コマンドライン引数を解釈する。不足時は Usage を表示して None を返す。"""
    parser = argparse.ArgumentParser(
        prog="export_review_meetings.py",
        description="検証会一覧を CSV / Excel に出力します。",
    )
    parser.add_argument("--format", choices=["csv", "excel"], help="出力形式")
    parser.add_argument("--output", help="出力ファイルパス")
    args = parser.parse_args(argv[1:])

    if not args.format or not args.output:
        # 注意事項に従い Usage は stdout に出力する。
        print(parser.format_help())
        return None
    return args


def _build_row(meeting: dict, summary: dict, model_code: str) -> dict:
    """検証会 + サマリー + 機種コードから、出力 1 行（ヘッダー名 -> 値）を作る。"""
    return {
        "機種コード": model_code,
        "機種名": meeting.get("modelName", ""),
        "検証会タイトル": meeting.get("title", ""),
        "イベントコード": meeting.get("eventCode", ""),
        "実施予定日": meeting.get("scheduledDate", ""),
        "ステータス": meeting.get("status", ""),
        "担当者名": meeting.get("organizerName", ""),
        "テスト総数": summary.get("totalCount", 0),
        "OK数": summary.get("okCount", 0),
        "NG数": summary.get("ngCount", 0),
        "保留数": summary.get("pendingCount", 0),
        "OK率": summary.get("okRate", ""),
        "備考": meeting.get("notes") or "",
    }


def _collect_rows(token: str) -> list[dict]:
    """検証会一覧を取得し、各検証会のサマリーを付与した行リストを組み立てる。"""
    meetings = get_review_meetings(token)

    # modelCode が検証会レスポンスに無い場合に備え、models から modelId -> modelCode を用意。
    model_code_by_id: dict = {model["id"]: model["modelCode"] for model in get_models(token)}

    rows: list[dict] = []
    for meeting in meetings:
        summary = get_test_summary(token, meeting["id"])
        model_code = meeting.get("modelCode") or model_code_by_id.get(meeting.get("modelId"), "")
        rows.append(_build_row(meeting, summary, model_code))
    return rows


def _write_csv(rows: list[dict], output: Path) -> None:
    """CSV を UTF-8-sig で書き込む（Excel での文字化け防止）。"""
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def _write_excel(rows: list[dict], output: Path) -> None:
    """openpyxl で Excel を書き込む（ヘッダー太字・グレー背景・列幅自動調整）。"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = SHEET_TITLE

    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

    # ヘッダー行
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.font = header_font
        cell.fill = header_fill

    # データ行
    for row in rows:
        sheet.append([row[header] for header in HEADERS])

    # 列幅の自動調整（ヘッダー・全セルの最大文字長を基準にする）
    for col_index, header in enumerate(HEADERS, start=1):
        max_length = len(str(header))
        for row in rows:
            max_length = max(max_length, len(str(row[header])))
        # 全角文字を考慮し少し余裕を持たせる
        sheet.column_dimensions[get_column_letter(col_index)].width = max_length + 4

    workbook.save(output)


def main(argv: list[str]) -> int:
    """エントリポイント。終了コードを返す（0=正常, 1=異常）。"""
    # ① 引数解釈
    args = _parse_args(argv)
    if args is None:
        return 1

    output = Path(args.output)

    # ② ログイン
    try:
        token = login(config.LOGIN_USERNAME, config.LOGIN_PASSWORD)
    except RuntimeError as e:
        print(e)
        return 1

    # ③④⑤ 検証会一覧 + サマリー取得、行の組み立て
    try:
        rows = _collect_rows(token)
    except RuntimeError as e:
        print(e)
        return 1
    except KeyError as e:
        print(f"APIレスポンス形式が想定と異なります: {e}")
        return 1

    # ⑥ 出力
    try:
        if args.format == "csv":
            _write_csv(rows, output)
        else:
            _write_excel(rows, output)
    except OSError as e:
        print(f"ファイルの書き込みに失敗しました: {e}")
        return 1

    # ⑦ 完了メッセージ
    print(f"出力が完了しました: {output} （形式: {args.format}, {len(rows)} 件）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
