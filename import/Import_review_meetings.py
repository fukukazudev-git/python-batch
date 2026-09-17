import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from api_client import login, get_users, create_review_meeting, auth_header

def normalize_headers(row: dict) -> dict:

def apply_defaults(row: dict) -> dict:

def validate(row: dict) -> list[str]:

