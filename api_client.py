from config import API_BASE_URL
import requests

BASE = API_BASE_URL

def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}",
            "Content-type": "application/json"}

def login(username: str,
          password: str) -> str:
    """
    レスポンスのtokenを返す
    失敗時はRuntimeErrorを送出
    """
    try:
        resp = requests.post(f"{BASE}/api/auth/login", 
                                 json={"username": username, 
                                       "password": password}, 
                                       timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError("Login failed") from e
    return resp.json()["token"]

def get_users(token: str) -> list[dict]:
    """
    ユーザ一覧を返す
    """
    resp = requests.get(f"{BASE}/api/users", 
                        headers=auth_header(token), timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_models(token: str) -> list[dict]:
    """
    モデル一覧を返す
    """
    resp = requests.get(f"{BASE}/api/models", 
                        headers=auth_header(token), 
                        timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_review_meetings(token: str) -> list[dict]:
    """
    検証会一覧を返す
    """
    resp = requests.get(f"{BASE}/api/review-meetings", 
                        headers=auth_header(token), 
                        timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_test_summary(token: str, review_meeting_id: int) -> dict:
    """
    テスト結果サマリーを返す
    """
    resp = requests.get(f"{BASE}/api/review-meetings/{review_meeting_id}/test-summary", 
                        headers=auth_header(token), 
                        timeout=10)
    resp.raise_for_status()
    return resp.json()

def create_review_meeting(token: str, payload: dict) -> dict:
    """
    レスポンスのJSONを返す
    失敗時はRuntimeErrorを送出
    """
    try:
        resp = requests.post(f"{BASE}/api/review-meetings", 
                             headers=auth_header(token), 
                             json=payload, 
                             timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError("Create review meeting failed") from e
    return resp.json()