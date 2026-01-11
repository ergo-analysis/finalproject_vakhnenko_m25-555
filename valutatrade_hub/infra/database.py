import json
import os
from typing import Any, Dict

from ..infra.settings import settings


class DatabaseManager:
    """Singleton для управления JSON-ами """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.data_path = settings.get("data_path", "data/")
        os.makedirs(self.data_path, exist_ok=True)
        self._initialized = True
    
    def _get_file_path(self, filename: str) -> str:
        """Возвращает полный путь к файлу"""
        return os.path.join(self.data_path, filename)
    
    def read_json(self, filename: str, default: Any = None) -> Any:

        filepath = self._get_file_path(filename)
        
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default if default is not None else []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка чтения файла {filename}: {e}")
            return default if default is not None else []
    
    def write_json(self, filename: str, data: Any) -> bool:
        """Записывает данные в JSON файл"""
        filepath = self._get_file_path(filename)
        
        try:
            # Создаем временный файл для записи
            temp_path = filepath + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            #  замена
            if os.path.exists(filepath):
                os.remove(filepath)
            os.rename(temp_path, filepath)
            return True
        except IOError as e:
            print(f"Ошибка записи файла {filename}: {e}")
            return False
    
    def update_item(self, filename: str, key: str,
                     value: Any, id_field: str = "user_id") -> bool:
        """Обновляет элемент в JSON файле"""
        data = self.read_json(filename, [])
        
        if not isinstance(data, list):
            print(f"Файл {filename} должен содержать список")
            return False
        
        updated = False
        for i, item in enumerate(data):
            if isinstance(item, dict) and item.get(id_field) == value.get(id_field):
                data[i] = value
                updated = True
                break
        
        if not updated:
            data.append(value)
        
        return self.write_json(filename, data)
    
    def find_item(self, filename: str, condition: Dict[str, Any]) -> Any:

        """Находит элемент по условию"""
        data = self.read_json(filename, [])
        
        if not isinstance(data, list):
            return None
        
        for item in data:
            if isinstance(item, dict):
                match = True
                for key, val in condition.items():
                    if item.get(key) != val:
                        match = False
                        break
                if match:
                    return item
        
        return None


db = DatabaseManager()