import shlex
import sys
from typing import Optional
from ..core.usecases import UserManager, PortfolioManager
from ..core.currencies import get_all_currencies, FiatCurrency, CryptoCurrency
from ..infra.settings import settings as app_settings


class Interface:
    """CLI интерфейс для торгового симулятора"""
    
    def __init__(self):
        self.current_user_id: Optional[int] = None
        self.current_username: Optional[str] = None
        self.running = True
        self.settings = app_settings  # Импорт settings в конструкторе
    
    def login_user(self, user_id: int, username: str):
        self.current_user_id = user_id
        self.current_username = username
    
    def logout_user(self):
        self.current_user_id = None
        self.current_username = None
    
    def is_logged_in(self) -> bool:
        return self.current_user_id is not None
    
    def parse_arguments(self, args_list: list[str]) -> dict:
        parsed = {}
        i = 0
        while i < len(args_list):
            if args_list[i].startswith('--'):
                key = args_list[i][2:]
                if i + 1 < len(args_list) and not args_list[i + 1].startswith('--'):
                    parsed[key] = args_list[i + 1]
                    i += 2
                else:
                    parsed[key] = True
                    i += 1
            else:
                parsed['command'] = args_list[i]
                i += 1
        return parsed
    
    def show_help(self):
        print("\nДоступные команды:")
        print("  register --username <name> --password <pass>   - регистрация")
        print("  login --username <name> --password <pass>      - вход")
        print("  logout                                         - выход")
        print("  show-portfolio [--base <currency>]             - портфель")
        print("  buy --currency <code> --amount <number>        - купить")
        print("  sell --currency <code> --amount <number>       - продать")
        print("  get-rate --from <currency> --to <currency>     - курс")
        print("  list-currencies                                - список валют")
        print("  show-settings                                  - настройки")
        print("  reload-settings                                - перезагрузка настроек")
        print("  help                                           - справка")
        print("  exit                                           - выход")
        print()
    
    def register(self, args: dict) -> str:
        if 'username' not in args or 'password' not in args:
            return "Ошибка: требуется --username и --password"
        
        try:
            return UserManager.register(args['username'], args['password'])
        except ValueError as e:
            return f"Ошибка: {e}"
    
    def login(self, args: dict) -> str:
        if 'username' not in args or 'password' not in args:
            return "Ошибка: требуется --username и --password"
        
        try:
            user_id, message = UserManager.login(args['username'], args['password'])
            self.login_user(user_id, args['username'])
            return message
        except ValueError as e:
            return f"Ошибка: {e}"
    
    def logout(self, args: dict) -> str:
        if not self.is_logged_in():
            return "Вы не были в системе"
        
        username = self.current_username
        self.logout_user()
        return f"Вы вышли из системы. До свидания, {username}!"
    
    def show_portfolio(self, args: dict) -> str:
        if not self.is_logged_in():
            return "Ошибка: Сначала выполните login"
        
        base_currency = args.get('base', 'USD')
        
        try:
            portfolio_info = PortfolioManager.get_portfolio_info(
                self.current_user_id,
                base_currency
            )
            
            result = [f"\nПортфель пользователя '{self.current_username}' (база: {portfolio_info['base_currency']}):"]
            
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
    
    
    def buy(self, args: dict) -> str:
        if not self.is_logged_in():
            return "Ошибка: Сначала выполните login"
        
        if 'currency' not in args or 'amount' not in args:
            return "Ошибка: требуется --currency и --amount"
        
        try:
            amount = float(args['amount'])
            if amount <= 0:
                return "'amount' должен быть положительным числом"
            
            result = PortfolioManager.buy_currency(
                self.current_user_id,
                args['currency'].upper(),
                amount
            )
            
            # Формируем сообщение для пользователя
            return (f"Покупка выполнена: {result['amount']:.4f} {result['currency']} "
                   f"по курсу {result['rate']:.2f} USD/{result['currency']}\n"
                   f"Оценочная стоимость покупки: {result['estimated_cost']:.2f} USD")
            
        except ValueError as e:
            return f"Ошибка: {e}"
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    
    def sell(self, args: dict) -> str:
        if not self.is_logged_in():
            return "Ошибка: Сначала выполните login"
        
        if 'currency' not in args or 'amount' not in args:
            return "Ошибка: требуется --currency и --amount"
        
        try:
            amount = float(args['amount'])
            if amount <= 0:
                return "'amount' должен быть положительным числом"
            
            result = PortfolioManager.sell_currency(
                self.current_user_id,
                args['currency'].upper(),
                amount
            )
            
            # Формируем сообщение для пользователя
            return (f"Продажа выполнена: {result['amount']:.4f} {result['currency']} "
                   f"по курсу {result['rate']:.2f} USD/{result['currency']}\n"
                   f"Оценочная выручка: {result['estimated_revenue']:.2f} USD")
            
        except ValueError as e:
            return f"Ошибка: {e}"
        except Exception as e:
            return f"Ошибка: {str(e)}"
    

    def get_rate(self, args: dict) -> str:
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
    
    def list_currencies(self, args: dict) -> str:
        currencies = get_all_currencies()
        
        result = ["\nПоддерживаемые валюты:"]
        
        result.append("\nФиатные валюты:")
        for code, currency in currencies.items():
            if isinstance(currency, FiatCurrency):
                result.append(f"  {currency.get_display_info()}")
        
        result.append("\nКриптовалюты:")
        for code, currency in currencies.items():
            if isinstance(currency, CryptoCurrency):
                result.append(f"  {currency.get_display_info()}")
        
        result.append(f"\nВсего валют: {len(currencies)}")
        return "\n".join(result)
    
    def show_settings(self, args: dict) -> str:
        config = self.settings.get_all()
        result = ["\nТекущие настройки:"]
        
        for key, value in config.items():
            result.append(f"  {key}: {value}")
        
        return "\n".join(result)
    
    def reload_settings(self, args: dict) -> str:
        self.settings.reload()
        return "Настройки перезагружены"
    
    def execute_command(self, command_line: str) -> str:
        if not command_line.strip():
            return ""
        
        try:
            args_list = shlex.split(command_line)
            if not args_list:
                return ""
            
            command = args_list[0]
            parsed_args = self.parse_arguments(args_list[1:])
            
            command_handlers = {
                "register": self.register,
                "login": self.login,
                "logout": self.logout,
                "show-portfolio": self.show_portfolio,
                "buy": self.buy,
                "sell": self.sell,
                "get-rate": self.get_rate,
                "list-currencies": self.list_currencies,
                "show-settings": self.show_settings,
                "reload-settings": self.reload_settings,
            }
            
            if command == "help":
                self.show_help()
                return ""
            elif command in ["exit", "quit"]:
                self.running = False
                if self.is_logged_in():
                    username = self.current_username
                    self.logout_user()
                    return f"Вы вышли из системы. До свидания, {username}!"
                return "До свидания!"
            elif command in command_handlers:
                return command_handlers[command](parsed_args)
            else:
                return f"Неизвестная команда: {command}. Введите 'help' для списка команд."
        
        except Exception as e:
            return f"Ошибка выполнения команды: {str(e)}"
    
    def get_prompt(self) -> str:
        if self.is_logged_in():
            return f"{self.current_username}> "
        return "guest> "
    
    def run(self):
        print("=" * 50)
        print("   ValutaTrade Hub - Симулятор торговли валютой")
        print("=" * 50)
        self.show_help()
        
        if self.is_logged_in():
            print(f"Вы вошли как: {self.current_username}")
        
        while self.running:
            try:
                prompt = self.get_prompt()
                command_line = input(prompt).strip()
                
                if not command_line:
                    continue
                
                result = self.execute_command(command_line)
                
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


def main():
    cli = Interface()
    cli.run()


if __name__ == "__main__":
    main()