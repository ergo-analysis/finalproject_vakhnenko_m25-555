class InsufficientFundsError(Exception):
    def __init__(self, available: float, required: float, code: str):
        super().__init__(f"Недостаточно средств: доступно {available:.4f} {code}, требуется {required:.4f} {code}")
        self.available = available
        self.required = required
        self.code = code


class CurrencyNotFoundError(Exception):
    def __init__(self, code: str):
        super().__init__(f"Неизвестная валюта '{code}'")
        self.code = code


class ApiRequestError(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
        self.reason = reason


class UserNotFoundError(Exception):
    def __init__(self, username: str):
        super().__init__(f"Пользователь '{username}' не найден")
        self.username = username


class InvalidPasswordError(Exception):
    def __init__(self):
        super().__init__("Неверный пароль")