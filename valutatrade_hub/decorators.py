import functools
import logging
from datetime import datetime
from typing import Any, Callable


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
            
            try:
                # Извлекаем данные для логирования
                if action in ["REGISTER", "LOGIN"]:
                    # Для регистрации и входа: первый аргумент - username
                    if args and len(args) > 0:
                        log_data["user"] = f"'{args[0]}'"
                
                elif action in ["BUY", "SELL"]:
                    # Для покупки и продажи
                    if len(args) > 0:
                        log_data["user"] = str(args[0])
                    if len(args) > 1:
                        log_data["currency"] = f"'{args[1]}'"
                    if len(args) > 2:
                        log_data["amount"] = f"{args[2]:.4f}"
                    # Добавляем base='USD' как в тз
                    log_data["base"] = "'USD'"
                

                result = func(*args, **kwargs)
                
                if verbose and isinstance(result, dict):
                    if "rate" in result and result["rate"]:
                        log_data["rate"] = f"{result['rate']:.2f}"
                
                #чувствиетльный момент, надо сформировть все по тз
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