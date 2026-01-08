import json
import os
from typing import Any, Dict


class SettingsLoader:
    """Singleton для загрузки настроек приложения"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """Singleton реализован через __new__, 
        потому что реализация метакласса дольше и он сложнее для понимания, 
        если придется перерабатывать код в дальнейшем

        """
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Настройки по умолчанию
        self._default_config = {
            "data_path": "data/",
            "users_file": "users.json",
            "portfolios_file": "portfolios.json",
            "rates_file": "rates.json",
            "exchange_rates_file": "exchange_rates.json",
            "rates_ttl_seconds": 300,  # 5 минут
            "default_base_currency": "USD",
            "log_path": "logs/",
            "log_file": "actions.log",
            "log_format": "%(asctime)s - %(levelname)s - %(message)s",
            "supported_currencies": ["USD", "EUR", "GBP", "RUB", "JPY", "BTC", "ETH", "LTC", "ADA"],
            "default_usd_balance": 10000.0,
            "api_timeout": 10,
            "max_login_attempts": 3
        }
        
        # Загружаем  настройки юзера
        self._load_config()
        self._initialized = True
    
    def _load_config(self) -> None:

        """Загружает конфигурацию из config.json или использует значения по умолчанию"""
        config_file = "config.json"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)

                # обновляем настройки для юзера
                self._config = {**self._default_config, **user_config}
                print(f"Настройки загружены из {config_file}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Ошибка загрузки настроек: {e}. Используются настройки по умолчанию.")
                self._config = self._default_config
        else:
            self._config = self._default_config
            print("Файл config.json не найден. Используются настройки по умолчанию.")
    

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу"""
        return self._config.get(key, default)
    
    def reload(self) -> None:
        """Перезагружает конфигурацию из файла"""

        self._load_config()
        print("Настройки перезагружены")

    
    def get_all(self) -> Dict[str, Any]:
        """Возвращает все текущие настройки"""
        return self._config.copy()
    
    def set(self, key: str, value: Any) -> None:
        """Устанавливает значения настроек"""

        self._config[key] = value
    

    def save(self) -> None:

        try:
            with open("config.json", 'w') as f:
                json.dump(self._config, f, indent=4)
            print("Настройки сохранены")
        except IOError as e:
            print(f"Ошибка сохранения настроек: {e}")


settings = SettingsLoader()