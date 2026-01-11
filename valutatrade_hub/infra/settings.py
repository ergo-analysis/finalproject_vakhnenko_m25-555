import json
import os
from typing import Any, Dict


class SettingsLoader:
    """Singleton для загрузки настроек приложения"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """Singleton реализован через __new__, 
        потому что это простой и понятный подход, не требующий знания метаклассов
        """
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        #это запасные настройки, на случай, если json окажется недоступен
        self._fallback_config = {
            "data_path": "data/",
            "log_path": "logs/",
            "default_base_currency": "USD",
            "rates_ttl_seconds": 300
        }
        
        # Загружаем конфиг
        self._load_config()
        self._initialized = True
    
    def _load_config(self) -> None:
        """Загружает конфигурацию из config.json"""
        config_file = "config.json"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    self._config = json.load(f)
                print(f"Настройки успешно загружены из {config_file}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Ошибка загрузки {config_file}: {e}. Используются минимальные настройки.")
                self._config = self._fallback_config.copy()
        else:
            print(f"Файл {config_file} не найден. Используются минимальные настройки.")
            self._config = self._fallback_config.copy()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу"""
        return self._config.get(key, default)

    
    def get_all(self) -> Dict[str, Any]:
        """Возвращает копию всех текущих настроек""" #Оставлено про запас
        return self._config.copy()


settings = SettingsLoader()
