import functools
import logging
from datetime import datetime
from typing import Any, Callable, Dict


def log_action(action_name: str = None, verbose: bool = False):
    """
    Декоратор для записи логов операций
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger('actions')
            
            operation = action_name or func.__name__.upper()
            
            log_data = {
                'action': operation,
                'timestamp': datetime.now().isoformat(),
                'result': 'OK'
            }
            
            try:
                # Прямое извлечение аргументов для наших методов
                # 1. Для buy_currency/sell_currency: (user_id, currency_code, amount)
                # 2. Для register/login: (username, password)
                
                if operation in ['BUY', 'SELL']:
                    # Для методов покупки/продажи
                    if len(args) >= 1:
                        # user_id может быть args[0] для статических методов
                        # или args[1] для методов класса (где args[0] = self)
                        if isinstance(args[0], int):
                            log_data['user_id'] = args[0]
                        elif len(args) >= 2 and isinstance(args[1], int):
                            log_data['user_id'] = args[1]
                
                # Проверяем именованные аргументы (приоритет выше)
                if 'user_id' in kwargs:
                    log_data['user_id'] = kwargs['user_id']
                if 'username' in kwargs:
                    log_data['username'] = kwargs['username']
                if 'currency_code' in kwargs:
                    log_data['currency_code'] = kwargs['currency_code']
                elif 'currency' in kwargs:
                    log_data['currency_code'] = kwargs['currency']
                if 'amount' in kwargs:
                    log_data['amount'] = kwargs['amount']
                
                # Для позиционных аргументов функций
                if operation == 'REGISTER' or operation == 'LOGIN':
                    if len(args) >= 1 and isinstance(args[0], str):
                        log_data['username'] = args[0]
                
                # Выполняем основную функцию
                result = func(*args, **kwargs)
                
                # Добавляем детали при verbose=True
                if verbose and isinstance(result, dict):
                    if 'rate' in result and result['rate'] is not None:
                        log_data['rate'] = result['rate']
                    if 'estimated_cost' in result and result['estimated_cost'] is not None:
                        log_data['cost'] = result['estimated_cost']
                    if 'estimated_revenue' in result and result['estimated_revenue'] is not None:
                        log_data['revenue'] = result['estimated_revenue']
                    if 'currency' in result:
                        log_data['currency_code'] = result['currency']
                    if 'amount' in result:
                        log_data['amount'] = result['amount']
                
                # Форматируем и записываем лог
                log_message = _format_log_entry(log_data)
                logger.info(log_message)
                
                return result
                
            except Exception as e:
                # Логируем ошибку
                log_data['result'] = 'ERROR'
                log_data['error_type'] = type(e).__name__
                log_data['error_message'] = str(e)
                
                log_message = _format_log_entry(log_data)
                logger.error(log_message)
                
                # Пробрасываем исключение дальше
                raise
        
        return wrapper
    
    return decorator


def _format_log_entry(log_data: Dict[str, Any]) -> str:
    """Форматирование данных лога в строку"""
    parts = [log_data['action']]
    
    if 'user_id' in log_data:
        parts.append(f"user_id={log_data['user_id']}")
    elif 'username' in log_data:
        parts.append(f"username='{log_data['username']}'")
    
    if 'currency_code' in log_data:
        parts.append(f"currency='{log_data['currency_code']}'")
    
    if 'amount' in log_data:
        parts.append(f"amount={log_data['amount']:.4f}")
    
    if 'rate' in log_data and log_data['rate'] is not None:
        parts.append(f"rate={log_data['rate']:.2f}")
    
    if 'cost' in log_data and log_data['cost'] is not None:
        parts.append(f"cost={log_data['cost']:.2f}")
    
    if 'revenue' in log_data and log_data['revenue'] is not None:
        parts.append(f"revenue={log_data['revenue']:.2f}")
    
    parts.append(f"result={log_data['result']}")
    
    if log_data['result'] == 'ERROR':
        error_msg = log_data.get('error_message', '')
        if len(error_msg) > 50:
            error_msg = error_msg[:47] + "..."
        parts.append(f"error={log_data['error_type']}:{error_msg}")
    
    return " ".join(parts)