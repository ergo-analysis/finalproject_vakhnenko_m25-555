import hashlib
import json
import os
import secrets
from typing import Optional


def generate_salt() -> str:
    return secrets.token_hex(8)


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((password + salt).encode()).hexdigest()


def load_users() -> list:
    try:
        with open("data/users.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_users(users: list):
    os.makedirs("data", exist_ok=True)
    with open("data/users.json", "w") as f:
        json.dump(users, f, indent=2, default=str)


def load_portfolios() -> list:
    try:
        with open("data/portfolios.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_portfolios(portfolios: list):
    os.makedirs("data", exist_ok=True)
    with open("data/portfolios.json", "w") as f:
        json.dump(portfolios, f, indent=2, default=str)


def get_next_user_id() -> int:
    users = load_users()
    if not users:
        return 1
    return max(user["user_id"] for user in users) + 1


def find_user_by_username(username: str) -> Optional[dict]:
    users = load_users()
    for user in users:
        if user["username"] == username:
            return user
    return None


def get_user_portfolio(user_id: int) -> Optional[dict]:
    portfolios = load_portfolios()
    for portfolio in portfolios:
        if portfolio["user_id"] == user_id:
            return portfolio
    return None