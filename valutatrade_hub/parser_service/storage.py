import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from .config import ParserConfig


class RatesStorage:
    """Управление хранением курсов валют"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Создает необходимые директории"""
        os.makedirs(Path(self.config.RATES_FILE_PATH).parent, exist_ok=True)
        os.makedirs(Path(self.config.HISTORY_FILE_PATH).parent, exist_ok=True)
    
    def load_current_rates(self) -> Dict[str, Any]:
        """Загружает текущие курсы из кэша"""
        try:
            with open(self.config.RATES_FILE_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"pairs": {}, "last_refresh": None}
    
    def load_history(self) -> List[Dict[str, Any]]:
        """Загружает историю курсов"""
        try:
            with open(self.config.HISTORY_FILE_PATH, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return []
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def save_current_rates(self, rates: Dict[str, Dict[str, Any]]):
        """Сохраняет текущие курсы в кэш"""
        current_time = datetime.now().isoformat()
        
        # Загружаем существующие курсы, обновляется только то, что не обновлялись
        existing_data = self.load_current_rates()
        existing_pairs = existing_data.get("pairs", {})
        
        existing_pairs.update(rates)
        
        data = {
            "pairs": existing_pairs,
            "last_refresh": current_time,
            "source": "ParserService"
        }
        
        # Атомарная запись через временный файл, см. тз
        temp_file = f"{self.config.RATES_FILE_PATH}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        os.replace(temp_file, self.config.RATES_FILE_PATH)
    
    def save_to_history(self, rate_data: Dict[str, Any]):
        """Сохраняет курс в историю в формате как в ТЗ"""
        history = self.load_history()
        
        from_currency = rate_data.get("from_currency", "")
        to_currency = rate_data.get("to_currency", "")
        timestamp = rate_data.get("timestamp", "").replace("+00:00", "Z")
        
        if from_currency and to_currency and timestamp:
            # Формируем ID как было в тз
            clean_timestamp = timestamp.replace(":", "").replace("-", "").replace("T", "").replace("Z", "")
            record_id = f"{from_currency}_{to_currency}_{clean_timestamp}"
            
            history_record = {
                "id": record_id,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate_data.get("rate", 0.0),
                "timestamp": timestamp,
                "source": rate_data.get("source", "unknown"),
                "meta": rate_data.get("meta", {})
            }
            
            # добавить время
            history_record["meta"]["saved_at"] = datetime.now().isoformat() + "Z"
            
            # Проверяем, нет ли уже такой записи
            # и сохраняем историю
            existing_ids = [item.get("id", "") for item in history]
            if record_id not in existing_ids:
                history.append(history_record)
                
                with open(self.config.HISTORY_FILE_PATH, 'w') as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)
            else:
                # Обновляем существующую запись
                for i, item in enumerate(history):
                    if item.get("id") == record_id:
                        history[i] = history_record
                        with open(self.config.HISTORY_FILE_PATH, 'w') as f:
                            json.dump(history, f, indent=2, ensure_ascii=False)
                        break
    
    def update_history_from_rates(self, rates: Dict[str, Dict[str, Any]]):
        """Обновляет историю из текущих курсов"""
        for pair_key, rate_info in rates.items():
            if "_" in pair_key:
                from_currency, to_currency = pair_key.split("_", 1)
                
                history_record = {
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": rate_info.get("rate", 0.0),
                    "timestamp": rate_info.get("timestamp", ""),
                    "source": rate_info.get("source", "unknown"),
                    "meta": rate_info.get("meta", {})
                }
                
                self.save_to_history(history_record)