import requests

from config import API_BASE_URL as BASE


def auth_header(token: str) -> dict[str, str]:
    """HTTP ヘッダーを組み立てて返す。"""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def login(username: str, password: str) -> str:
    """
    レスポンスのtokenを返す
    失敗時はRuntimeErrorを送出
    """
    try:
        resp = requests.post(
            f"{BASE}/api/auth/login", json={"username": username, "password": password}, timeout=10
        )
        # エラー時は早い段階で例外に変換
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"ログインに失敗しました: {e}") from e
    return resp.json()["token"]


def _get(path: str, token: str) -> list | dict:
    """GET 共通処理。失敗時は RuntimeError を送出する。"""
    try:
        resp = requests.get(f"{BASE}{path}", headers=auth_header(token), timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"GET {path} に失敗しました: {e}") from e
    return resp.json()


def get_users(token: str) -> list[dict]:
    """GET /api/users のユーザー一覧を返す。"""
    return _get("/api/users", token)


def get_models(token: str) -> list[dict]:
    """GET /api/models のモデル一覧を返す。"""
    return _get("/api/models", token)


def get_review_meetings(token: str) -> list[dict]:
    """GET /api/review-meetings の検証会一覧を返す。"""
    return _get("/api/review-meetings", token)


def get_test_summary(token: str, review_meeting_id: int) -> dict:
    """指定検証会のテスト結果サマリー（GET .../test-summary）を返す。"""
    return _get(f"/api/review-meetings/{review_meeting_id}/test-summary", token)


def create_review_meeting(token: str, payload: dict) -> dict:
    """
    レスポンスのJSONを返す
    失敗時はRuntimeErrorを送出
    """
    try:
        resp = requests.post(
            f"{BASE}/api/review-meetings", headers=auth_header(token), json=payload, timeout=10
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"検証会の作成に失敗しました: {e}") from e
    return resp.json()
