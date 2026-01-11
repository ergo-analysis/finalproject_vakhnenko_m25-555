import functools
import json
import logging
from pathlib import Path
from typing import Any, Callable


def load_users():
    """Загружает пользователей из файла users.json"""
    users_file = Path("data/users.json")
    if users_file.exists():
        with open(users_file, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        # Создаем маппинг id:username
        user_map = {}
        for user in users_data:
            user_map[user["user_id"]] = user["username"]
        return user_map
    return {}


def log_action(action: str, verbose: bool = False):
    """
    Декоратор для логирования действий.
    """
    
    def decorator(func: Callable) -> Callable:
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger("valutatrade")
            
            log_data = {
                "action": action,
                "result": "OK"
            }
            
            # Загружаем маппинг id:username
            user_map = load_users()
            
            try:
                # Извлекаем данные для логирования
                if action in ["REGISTER", "LOGIN"]:
                    # Для регистрации и входа: первый аргумент --username
                    if args and len(args) > 0:
                        log_data["user"] = f"'{args[0]}'"
                
                elif action in ["BUY", "SELL"]:
                    user_id = args[0] if len(args) > 0 else None
                    
                    # достаем имя юзера по ид
                    # Если не найден, используем ид
                    if user_id is not None and isinstance(user_id, int):
                        username = user_map.get(user_id, str(user_id))  
                        log_data["user"] = f"'{username}'"
                    else:
                        log_data["user"] = f"'{user_id}'"
                        
                    if len(args) > 1:
                        log_data["currency"] = f"'{args[1]}'"
                    if len(args) > 2:
                        log_data["amount"] = f"{args[2]:.4f}"
                    log_data["base"] = "'USD'"
                

                result = func(*args, **kwargs)
                
                if verbose and isinstance(result, dict):
                    if "rate" in result and result["rate"]:
                        log_data["rate"] = f"{result['rate']:.2f}"
                
                #чувствоительный момент, надо сформировать все по тз
                log_parts = [f"{log_data['action']}"]
                
                if "user" in log_data:
                    log_parts.append(f"user={log_data['user']}")
                if "currency" in log_data:
                    log_parts.append(f"currency={log_data['currency']}")
                if "amount" in log_data:
                    log_parts.append(f"amount={log_data['amount']}")
                if "rate" in log_data:
                    log_parts.append(f"rate={log_data['rate']}")
                if "base" in log_data:
                    log_parts.append(f"base={log_data['base']}")
                
                log_parts.append(f"result={log_data['result']}")
                
                logger.info(" ".join(log_parts))
                
                return result
                
            except Exception as e:

                log_data["result"] = "ERROR"
                
                # строка лога где ошибка
                log_parts = [
                    f"{log_data['action']}",
                    f"result={log_data['result']}",
                    f"error_type={type(e).__name__}",
                    f"error_message='{str(e)}'"
                ]
                
                logger.error(" ".join(log_parts))
                
                # Пробрасываем исключение дальше
                raise
        
        return wrapper
    
    return decorator