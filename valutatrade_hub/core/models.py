import hashlib
import json
from datetime import datetime
from typing import Dict, Optional


class User:
    def __init__(self, user_id: int, username: str, hashed_password: str, 
                 salt: str, registration_date: datetime):
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @hashed_password.setter
    def hashed_password(self, value: str):
        if len(value) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._hashed_password = value

    def get_user_info(self) -> str:
        return (f"ID: {self._user_id}, "
                f"Имя: {self._username}, "
                f"Дата регистрации: {self._registration_date}")

    def change_password(self, new_password: str):
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        new_hash = hashlib.sha256((new_password + self._salt).encode()).hexdigest()
        self._hashed_password = new_hash

    def verify_password(self, password: str) -> bool:
        test_hash = hashlib.sha256((password + self._salt).encode()).hexdigest()
        return test_hash == self._hashed_password

    def to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"])
        )


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self._balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float):
        if not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = round(value, 8)

    def deposit(self, amount: float):
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")
        self.balance += amount

    def withdraw(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной")
        if amount > self._balance:
            raise ValueError(f"Недостаточно средств. Доступно: {self._balance}")
        self.balance -= amount
        return amount

    def get_balance_info(self) -> str:
        return f"{self.currency_code}: {self._balance:.8f}"

    def to_dict(self) -> dict:
        return {
            "currency_code": self.currency_code,
            "balance": self._balance
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Wallet':
        return cls(
            currency_code=data["currency_code"],
            balance=data["balance"]
        )


class Portfolio:
    def __init__(self, user_id: int, wallets: Dict[str, Wallet] = None):
        self._user_id = user_id
        self._wallets = wallets or {}

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> Dict[str, Wallet]:
        return self._wallets.copy()

    def add_currency(self, currency_code: str):
        if currency_code not in self._wallets:
            self._wallets[currency_code] = Wallet(currency_code)

    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        return self._wallets.get(currency_code)

    def get_total_value(self, base_currency: str = 'USD') -> float:
        total = 0.0
        for wallet in self._wallets.values():
            if wallet.currency_code == base_currency:
                total += wallet.balance
            else:
                rate = self._get_exchange_rate(wallet.currency_code, base_currency)
                if rate:
                    total += wallet.balance * rate
        return total

    def _get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        rates = self._load_rates()
        key = f"{from_currency}_{to_currency}"
        return rates.get(key, {}).get("rate", 0.0)

    def _load_rates(self) -> dict:
        try:
            with open("data/rates.json", "r") as f:
                return json.load(f).get("pairs", {})
        except FileNotFoundError:
            return {}

    def to_dict(self) -> dict:
        wallets_dict = {}
        for code, wallet in self._wallets.items():
            wallets_dict[code] = wallet.to_dict()
        return {
            "user_id": self._user_id,
            "wallets": wallets_dict
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Portfolio':
        wallets = {}
        for code, wallet_data in data.get("wallets", {}).items():
            wallets[code] = Wallet.from_dict(wallet_data)
        return cls(user_id=data["user_id"], wallets=wallets)