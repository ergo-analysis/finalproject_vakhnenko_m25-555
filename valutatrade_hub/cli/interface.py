import shlex
import sys
from typing import Optional, List
from ..core.usecases import UserManager, PortfolioManager


class SessionManager:
    _current_user_id: Optional[int] = None
    _current_username: Optional[str] = None
    
    @classmethod
    def login(cls, user_id: int, username: str):
        cls._current_user_id = user_id
        cls._current_username = username
    
    @classmethod
    def logout(cls):
        cls._current_user_id = None
        cls._current_username = None
    
    @classmethod
    def is_logged_in(cls) -> bool:
        return cls._current_user_id is not None
    
    @classmethod
    def get_current_user_id(cls) -> Optional[int]:
        return cls._current_user_id
    
    @classmethod
    def get_current_username(cls) -> Optional[str]:
        return cls._current_username


def parse_args(args: List[str]) -> tuple:
    """Парсит аргументы командной строки"""
    parsed_args = {}
    i = 0
    while i < len(args):
        if args[i].startswith('--'):
            key = args[i][2:]
            if i + 1 < len(args) and not args[i + 1].startswith('--'):
                parsed_args[key] = args[i + 1]
                i += 2
            else:
                parsed_args[key] = True
                i += 1
        else:
            parsed_args['command'] = args[i]
            i += 1
    return parsed_args


def print_help():
    """Выводит справку по командам"""
    print("\nДоступные команды:")
    print("  register --username <name> --password <pass>   - регистрация нового пользователя")
    print("  login --username <name> --password <pass>      - вход в систему")
    print("  logout                                         - выход из системы")
    print("  show-portfolio [--base <currency>]             - показать портфель")
    print("  buy --currency <code> --amount <number>        - купить валюту")
    print("  sell --currency <code> --amount <number>       - продать валюту")
    print("  get-rate --from <currency> --to <currency>     - получить курс валюты")
    print("  help                                           - показать эту справку")
    print("  exit                                           - выйти из программы")
    print()


def register(args: dict) -> str:
    """Обработка команды регистрации""" 
    if 'username' not in args or 'password' not in args:
        return "Ошибка: требуется --username и --password"
    
    try:
        return UserManager.register(args['username'], args['password'])
    except ValueError as e:
        return f"Ошибка: {e}"


def login(args: dict) -> str:
    """Обработка команды входа"""
    if 'username' not in args or 'password' not in args:
        return "Ошибка: требуется --username и --password"
    
    try:
        user_id, message = UserManager.login(args['username'], args['password'])
        SessionManager.login(user_id, args['username'])
        return message
    except ValueError as e:
        return f"Ошибка: {e}"


def logout(args: dict) -> str:
    """Обработка команды выхода"""
    if not SessionManager.is_logged_in():
        return "Вы не были в системе"
    
    username = SessionManager.get_current_username()
    SessionManager.logout()
    return f"Вы вышли из системы. До свидания, {username}!"


def show_portfolio(args: dict) -> str:
    """Обработка команды показа портфеля"""
    if not SessionManager.is_logged_in():
        return "Ошибка: Сначала выполните login"
    
    base_currency = args.get('base', 'USD')
    
    try:
        portfolio_info = PortfolioManager.get_portfolio_info(
            SessionManager.get_current_user_id(),
            base_currency
        )
        
        result = [f"\nПортфель пользователя '{SessionManager.get_current_username()}' (база: {portfolio_info['base_currency']}):"]
        
        if not portfolio_info["wallets"]:
            result.append("  У вас пока нет кошельков")
            return "\n".join(result)
        
        for wallet in portfolio_info["wallets"]:
            result.append(f"  - {wallet['currency']}: {wallet['balance']:.4f} → {wallet['value_in_base']:.2f} {portfolio_info['base_currency']}")
        
        result.append(f"  {'-' * 40}")
        result.append(f"  ИТОГО: {portfolio_info['total_value']:,.2f} {portfolio_info['base_currency']}")
        
        return "\n".join(result)
    
    except Exception as e:
        return f"Ошибка: {e}"


def buy(args: dict) -> str:
    """Обработка команды покупки"""
    if not SessionManager.is_logged_in():
        return "Ошибка: Сначала выполните login"
    
    if 'currency' not in args or 'amount' not in args:
        return "Ошибка: требуется --currency и --amount"
    
    try:
        amount = float(args['amount'])
        if amount <= 0:
            return "'amount' должен быть положительным числом"
        
        return PortfolioManager.buy_currency(
            SessionManager.get_current_user_id(),
            args['currency'].upper(),
            amount
        )
    except ValueError as e:
        return f"Ошибка: {e}"
    except Exception as e:
        return f"Ошибка: {str(e)}"


def sell(args: dict) -> str:
    """Обработка команды продажи"""
    if not SessionManager.is_logged_in():
        return "Ошибка: Сначала выполните login"
    
    if 'currency' not in args or 'amount' not in args:
        return "Ошибка: требуется --currency и --amount"
    
    try:
        amount = float(args['amount'])
        if amount <= 0:
            return "'amount' должен быть положительным числом"
        
        return PortfolioManager.sell_currency(
            SessionManager.get_current_user_id(),
            args['currency'].upper(),
            amount
        )
    except ValueError as e:
        return f"Ошибка: {e}"
    except Exception as e:
        return f"Ошибка: {str(e)}"


def get_rate(args: dict) -> str:
    """Обработка команды получения курса"""
    if 'from' not in args or 'to' not in args:
        return "Ошибка: требуется --from и --to"
    
    try:
        rate_info = PortfolioManager.get_exchange_rate(args['from'], args['to'])
        
        return (f"\nКурс {rate_info['from_currency']}→{rate_info['to_currency']}: {rate_info['rate']:.8f}\n"
                f"Время обновления: {rate_info['updated_at']}\n"
                f"Источник: {rate_info['source']}\n"
                f"Обратный курс {rate_info['to_currency']}→{rate_info['from_currency']}: {rate_info['inverse_rate']:.8f}")
    
    except ValueError as e:
        return f"Ошибка: {e}"


def execute_command(command_line: str) -> str:
    if not command_line.strip():
        return ""
    
    try:
        args_list = shlex.split(command_line)
        if not args_list:
            return ""
        
        command = args_list[0]
        parsed_args = parse_args(args_list[1:])
        
        match command:
            case "register":
                return register(parsed_args)
            case "login":
                return login(parsed_args)
            case "logout":
                return logout(parsed_args)
            case "show-portfolio":
                return show_portfolio(parsed_args)
            case "buy":
                return buy(parsed_args)
            case "sell":
                return sell(parsed_args)
            case "get-rate":
                return get_rate(parsed_args)
            case "help":
                show_help()
                return ""
            case "exit" | "quit":
                if SessionManager.is_logged_in():
                    username = SessionManager.get_current_username()
                    SessionManager.logout()
                    return f"Вы вышли из системы. До свидания, {username}!"
                return "До свидания!"
            case _:
                return f"Неизвестная команда: {command}. Введите 'help' для списка команд."
    
    except Exception as e:
        return f"Ошибка выполнения команды: {str(e)}"



def main():
    """Основная функция интерактивного CLI"""
    print("=" * 50)
    print("   ValutaTrade Hub - Симулятор торговли валютой")
    print("=" * 50)
    print_help()
    
    if SessionManager.is_logged_in():
        print(f"Вы вошли как: {SessionManager.get_current_username()}")
    
    while True:
        try:
            if SessionManager.is_logged_in():
                prompt = f"{SessionManager.get_current_username()}> "
            else:
                prompt = "guest> "
            
            command_line = input(prompt).strip()
            
            if not command_line:
                continue
            
            result = execute_command(command_line)
            
            if result:
                print(result)
            
            if command_line.strip() in ["exit", "quit"]:
                break
                
        except KeyboardInterrupt:
            print("\n\nДля выхода введите 'exit' или 'quit'")
        except EOFError:
            print("\n\nДо свидания!")
            break
        except Exception as e:
            print(f"\nНепредвиденная ошибка: {str(e)}")
            continue


if __name__ == "__main__":
    main()