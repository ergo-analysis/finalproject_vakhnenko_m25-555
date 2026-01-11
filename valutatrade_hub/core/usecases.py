from datetime import datetime
from typing import Any, Dict

from ..decorators import log_action
from ..infra.database import db
from ..infra.settings import settings
from .currencies import get_currency
from .exceptions import ApiRequestError, CurrencyNotFoundError, InsufficientFundsError, InvalidPasswordError, UserNotFoundError
from .models import Portfolio


class UserManager:
    @staticmethod
    @log_action("REGISTER")
    def register(username: str, password: str) -> str:
        existing_user = db.find_item("users.json", {"username": username})
        if existing_user:
            raise ValueError(f"Имя пользователя '{username}' уже занято")
        
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        
        users = db.read_json("users.json", [])
        user_id = max([u.get("user_id", 0) for u in users], default=0) + 1
        
        import hashlib
        import secrets
        
        salt = secrets.token_hex(8)
        hashed_pw = hashlib.sha256((password + salt).encode()).hexdigest()
        
        user_data = {
            "user_id": user_id,
            "username": username,
            "hashed_password": hashed_pw,
            "salt": salt,
            "registration_date": datetime.now().isoformat()
        }
        
        users.append(user_data)
        db.write_json("users.json", users)
        
        portfolio_data = {
            "user_id": user_id,
            "wallets": {
                "USD": {
                    "currency_code": "USD",
                    "balance": settings.get("default_usd_balance", 10000.0)
                }
            }
        }
        
        portfolios = db.read_json("portfolios.json", [])
        portfolios.append(portfolio_data)
        db.write_json("portfolios.json", portfolios)
        
        return f"Пользователь '{username}' зарегистрирован (id={user_id})."

    @staticmethod
    @log_action("LOGIN")
    def login(username: str, password: str) -> tuple[int, str]:
        user_data = db.find_item("users.json", {"username": username})
        if not user_data:
            raise UserNotFoundError(username)
        
        import hashlib
        salt = user_data.get("salt", "")
        hashed_pw = hashlib.sha256((password + salt).encode()).hexdigest()
        
        if hashed_pw != user_data.get("hashed_password"):
            raise InvalidPasswordError()
        
        return user_data["user_id"], f"Вы вошли как '{username}'"


class PortfolioManager: 
    @staticmethod
    def get_portfolio_info(user_id: int, base_currency: str = None) -> Dict[str, Any]:
        if base_currency is None:
            base_currency = settings.get("default_base_currency", "USD")
        
        try:
            get_currency(base_currency)
        except CurrencyNotFoundError:
            raise CurrencyNotFoundError(base_currency)
        
        portfolio_data = db.find_item("portfolios.json", {"user_id": user_id})
        if not portfolio_data:
            portfolio = Portfolio(user_id)
        else:
            portfolio = Portfolio.from_dict(portfolio_data)
        
        # Загружаем данные
        rates_data = PortfolioManager._load_rates()
        #rates = rates_data.get("pairs", {})
        
        if PortfolioManager._are_rates_stale(rates_data):
            print("Внимание: курсы валют устарели. Рекомендуется обновить через update-rates")
        
        result = {
            "wallets": [],
            "total_value": 0.0,
            "base_currency": base_currency,
            "rates_fresh": not PortfolioManager._are_rates_stale(rates_data)
        }
        
        total = 0.0
        for wallet in portfolio.wallets.values():
            if wallet.currency_code == base_currency:
                value = wallet.balance
            else:

                try:
                    rate_info = PortfolioManager.get_exchange_rate(wallet.currency_code, base_currency)
                    rate = rate_info["rate"]
                    value = wallet.balance * rate
                except ApiRequestError:
                    # Если курс не найден, ставим 0.0 и пишем предупреждение
                    print(f"Предупреждение: Не удалось получить курс {wallet.currency_code}→{base_currency}")
                    rate = 0.0
                    value = 0.0
            
            result["wallets"].append({
                "currency": wallet.currency_code,
                "balance": wallet.balance,
                "value_in_base": value
            })
            total += value
        
        result["total_value"] = total
        return result


    @staticmethod
    @log_action("BUY", verbose=True)
    def buy_currency(user_id: int, currency_code: str, amount: float) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        
        try:
            get_currency(currency_code)
        except CurrencyNotFoundError:
            raise CurrencyNotFoundError(currency_code)
        
        portfolio_data = db.find_item("portfolios.json", {"user_id": user_id})
        if not portfolio_data:
            portfolio = Portfolio(user_id)
        else:
            portfolio = Portfolio.from_dict(portfolio_data)
        
        # Правильно загружаем курсы - получаем полные данные, затем извлекаем pairs
        rates_data = PortfolioManager._load_rates()
        rates = rates_data.get("pairs", {})  # Исправлено: получаем пары из данных
        rate_key = f"{currency_code}_USD"
        
        if rate_key not in rates:
            raise ApiRequestError(f"Курс {currency_code}→USD недоступен")
        
        rate = rates[rate_key]["rate"]
        cost_usd = amount * rate
        
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet or usd_wallet.balance < cost_usd:
            raise InsufficientFundsError(
                available=usd_wallet.balance if usd_wallet else 0.0,
                required=cost_usd,
                code="USD"
            )
        
        usd_wallet.withdraw(cost_usd)
        
        target_wallet = portfolio.get_wallet(currency_code)
        old_target_balance = target_wallet.balance if target_wallet else 0.0
        
        if not target_wallet:
            portfolio.add_currency(currency_code)
            target_wallet = portfolio.get_wallet(currency_code)
        
        target_wallet.deposit(amount)
        
        db.update_item("portfolios.json", "user_id", portfolio.to_dict())
        
        return {
            "user_id": user_id,
            "currency": currency_code,
            "amount": amount,
            "rate": rate,
            "estimated_cost": cost_usd,
            "old_balance": old_target_balance,
            "new_balance": target_wallet.balance
        }


    @staticmethod
    @log_action("SELL", verbose=True)
    def sell_currency(user_id: int, currency_code: str, amount: float) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        
        try:
            get_currency(currency_code)
        except CurrencyNotFoundError:
            raise CurrencyNotFoundError(currency_code)
        
        portfolio_data = db.find_item("portfolios.json", {"user_id": user_id})
        if not portfolio_data:
            portfolio = Portfolio(user_id)
        else:
            portfolio = Portfolio.from_dict(portfolio_data)
        
        target_wallet = portfolio.get_wallet(currency_code)
        if not target_wallet:
            raise ValueError(f"У вас нет кошелька '{currency_code}'.")
        
        old_target_balance = target_wallet.balance
        
        if target_wallet.balance < amount:
            raise InsufficientFundsError(
                available=old_target_balance,
                required=amount,
                code=currency_code
            )
        
        # Правильно загружаем курсы - получаем полные данные, затем извлекаем pairs
        rates_data = PortfolioManager._load_rates()
        rates = rates_data.get("pairs", {})  # Исправлено: получаем пары из данных
        rate_key = f"{currency_code}_USD"
        
        if rate_key not in rates:
            raise ApiRequestError(f"Курс {currency_code}→USD недоступен")
        
        rate = rates[rate_key]["rate"]
        revenue_usd = amount * rate
        
        target_wallet.withdraw(amount)
        
        usd_wallet = portfolio.get_wallet("USD")
        
        if not usd_wallet:
            portfolio.add_currency("USD")
            usd_wallet = portfolio.get_wallet("USD")
        
        usd_wallet.deposit(revenue_usd)
        
        db.update_item("portfolios.json", "user_id", portfolio.to_dict())
        
        return {
            "user_id": user_id,
            "currency": currency_code,
            "amount": amount,
            "rate": rate,
            "estimated_revenue": revenue_usd,
            "old_balance": old_target_balance,
            "new_balance": target_wallet.balance
        }

    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str) -> Dict[str, Any]:
        try:
            get_currency(from_currency)
            get_currency(to_currency)
        except CurrencyNotFoundError as e:
            raise CurrencyNotFoundError(e.code)
        
        # Загружаем полные данные
        rates_data = PortfolioManager._load_rates()
        rates = rates_data.get("pairs", {})
        last_refresh = rates_data.get("last_refresh")
        
        is_stale = PortfolioManager._are_rates_stale(rates_data)
        
        # Проверяем прямой курс
        rate_key = f"{from_currency}_{to_currency}"
        if rate_key in rates:
            rate_data = rates[rate_key]
            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate_data["rate"],
                "updated_at": rate_data.get("timestamp", last_refresh),
                "source": rate_data["source"],
                "inverse_rate": 1 / rate_data["rate"] if rate_data["rate"] != 0 else 0,
                "is_fresh": not is_stale
            }
        
        # Проверяем обратный курс
        reverse_key = f"{to_currency}_{from_currency}"
        if reverse_key in rates:
            rate_data = rates[reverse_key]
            rate = 1 / rate_data["rate"] if rate_data["rate"] != 0 else 0
            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate,
                "updated_at": rate_data.get("timestamp", last_refresh),
                "source": rate_data["source"],
                "inverse_rate": rate_data["rate"],
                "is_fresh": not is_stale
            }
        
        # Расчет через USD (косвенный курс)
        if from_currency != "USD" and to_currency != "USD":
            from_to_usd_key = f"{from_currency}_USD"
            to_to_usd_key = f"{to_currency}_USD"
            
            if from_to_usd_key in rates and to_to_usd_key in rates:
                from_rate = rates[from_to_usd_key]["rate"]
                to_rate = rates[to_to_usd_key]["rate"]
                
                if to_rate != 0:
                    rate = from_rate / to_rate
                    # Берем самый свежий timestamp
                    timestamp1 = rates[from_to_usd_key].get("timestamp")
                    timestamp2 = rates[to_to_usd_key].get("timestamp")
                    updated_at = timestamp1 if timestamp1 and (not timestamp2 or timestamp1 > timestamp2) else timestamp2
                    
                    return {
                        "from_currency": from_currency,
                        "to_currency": to_currency,
                        "rate": rate,
                        "updated_at": updated_at or last_refresh,
                        "source": f"{rates[from_to_usd_key]['source']}/{rates[to_to_usd_key]['source']}",
                        "inverse_rate": 1 / rate if rate != 0 else 0,
                        "is_fresh": not is_stale
                    }
        
        raise ApiRequestError(f"Курс {from_currency}→{to_currency} недоступен. Попробуйте обновить курсы через 'update-rates'.")

    @staticmethod
    def _load_rates() -> Dict[str, Any]:
        """Загружает полные данные о курсах (включая last_refresh)"""
        try:
            return db.read_json("rates.json", {})
        except Exception:
            return {"pairs": {}, "last_refresh": None}

    @staticmethod
    def _are_rates_stale(rates_data: Dict[str, Any]) -> bool:
        """Проверяет актуальность курсов"""
        if not rates_data or not isinstance(rates_data, dict):
            return True
        
        ttl_seconds = settings.get("rates_ttl_seconds", 300)
        last_refresh = rates_data.get("last_refresh")
        
        if not last_refresh:
            return True
        
        try:
            from datetime import datetime
            # Обрабатываем разные форматы времени
            clean_time = last_refresh.replace('Z', '+00:00') if last_refresh.endswith('Z') else last_refresh
            last_update = datetime.fromisoformat(clean_time)
            
            now = datetime.now()
            age = (now - last_update).total_seconds()
            return age > ttl_seconds
        except (ValueError, TypeError):
            return True