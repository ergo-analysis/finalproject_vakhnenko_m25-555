from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс для валют"""
    
    def __init__(self, name: str, code: str):
        if not name or not name.strip():
            raise ValueError("Название валюты не может быть пустым")
        
        if not 2 <= len(code) <= 5:
            raise ValueError("Код валюты должен содержать 2-5 символов")
        
        if not code.isupper():
            raise ValueError("Код валюты должен быть в верхнем регистре")
        
        self._name = name
        self._code = code
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def code(self) -> str:
        return self._code
    
    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает валюту как строку"""
        pass
    
    def __str__(self) -> str:
        return self.get_display_info()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self._name}', code='{self._code}')"


class FiatCurrency(Currency):
    """Класс для фиатных валют"""
    
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self._issuing_country = issuing_country
    
    @property
    def issuing_country(self) -> str:
        return self._issuing_country
    
    def get_display_info(self) -> str:
        return f"[FIAT] {self._code} — {self._name} (Issuing: {self._issuing_country})"


class CryptoCurrency(Currency):
    """Класс для криптовалют"""
    
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        super().__init__(name, code)
        self._algorithm = algorithm
        self._market_cap = market_cap
    
    @property
    def algorithm(self) -> str:
        return self._algorithm
    
    @property
    def market_cap(self) -> float:
        return self._market_cap
    
    @market_cap.setter
    def market_cap(self, value: float):
        if value < 0:
            raise ValueError("Рыночная капитализация не может быть отрицательной")
        self._market_cap = value
    
    def get_display_info(self) -> str:
        cap_str = f"{self._market_cap:.2e}" if self._market_cap >= 1e6 else f"{self._market_cap:,.2f}"
        return f"[CRYPTO] {self._code} — {self._name} (Algo: {self._algorithm}, MCAP: {cap_str})"


# Реестр поддерживаемых валют
_REGISTRY = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "JPY": FiatCurrency("Japanese Yen", "JPY", "Japan"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1_120_000_000_000),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 420_000_000_000),
    "LTC": CryptoCurrency("Litecoin", "LTC", "Scrypt", 6_500_000_000),
    "ADA": CryptoCurrency("Cardano", "ADA", "Ouroboros", 14_000_000_000),
}


def get_currency(code: str) -> Currency:
    """Фабричный метод для получения объекта валюты"""
    code = code.upper()
    if code not in _REGISTRY:
        raise CurrencyNotFoundError(code)
    return _REGISTRY[code]


def get_all_currencies() -> dict:
    """Возвращает словарь всех поддерживаемых валют"""
    return _REGISTRY.copy()


def get_currency_type(code: str) -> str:
    """Возвращает тип валюты: 'fiat' или 'crypto'"""
    currency = get_currency(code)
    return "fiat" if isinstance(currency, FiatCurrency) else "crypto"


def get_supported_codes() -> list:
    """Возвращает список поддерживаемых кодов валют"""
    return list(_REGISTRY.keys())