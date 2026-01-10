import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ParserConfig:
    """Конфигурация для сервиса парсинга"""

    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")
    
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"
    
    # это базовая валюта как в тз
    BASE_FIAT_CURRENCY: str = "USD"
    
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB", "JPY")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "LTC", "ADA")
    
    # словарь для криптовалютных кодов на CoinGecko
    CRYPTO_ID_MAP: Dict[str, str] = field(default_factory=lambda: {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "LTC": "litecoin",
        "ADA": "cardano"
    })
    
    # Таймаут запросов в секундах
    REQUEST_TIMEOUT: int = 10
    
    # Пути к файлам
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"
    
    def validate(self) -> bool:
        """Проверяет валидность конфигурации"""
        if not self.EXCHANGERATE_API_KEY:
            raise ValueError("API ключ для ExchangeRate-API не найден. Установите переменную окружения EXCHANGERATE_API_KEY")
        return True