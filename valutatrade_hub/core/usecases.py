import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from .models import User, Portfolio, Wallet
from .currencies import get_currency
from .exceptions import (
    CurrencyNotFoundError, InsufficientFundsError, 
    UserNotFoundError, InvalidPasswordError, ApiRequestError
)
from ..infra.settings import settings
from ..infra.database import db
from ..decorators import log_action


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
        
        rates = PortfolioManager._load_rates()
        
        if PortfolioManager._are_rates_stale(rates):
            print("Внимание: курсы валют устарели. Рекомендуется обновить через update-rates")
        
        result = {
            "wallets": [],
            "total_value": 0.0,
            "base_currency": base_currency,
            "rates_fresh": not PortfolioManager._are_rates_stale(rates)
        }
        
        total = 0.0
        for wallet in portfolio.wallets.values():
            if wallet.currency_code == base_currency:
                value = wallet.balance
            else:
                rate_key = f"{wallet.currency_code}_{base_currency}"
                rate = rates.get(rate_key, {}).get("rate", 0.0)
                value = wallet.balance * rate
            
            result["wallets"].append({
                "currency": wallet.currency_code,
                "balance": wallet.balance,
                "value_in_base": value
            })
            total += value
        
        if base_currency in portfolio.wallets:
            total += portfolio.wallets[base_currency].balance
        
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
        
        rates = PortfolioManager._load_rates()
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
        
        # Сохраняем старый баланс
        old_usd_balance = usd_wallet.balance
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
        
        rates = PortfolioManager._load_rates()
        rate_key = f"{currency_code}_USD"
        
        if rate_key not in rates:
            raise ApiRequestError(f"Курс {currency_code}→USD недоступен")
        
        rate = rates[rate_key]["rate"]
        revenue_usd = amount * rate
        
        target_wallet.withdraw(amount)
        
        usd_wallet = portfolio.get_wallet("USD")
        old_usd_balance = usd_wallet.balance if usd_wallet else 0.0
        
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
        
        rates = PortfolioManager._load_rates()
        
        is_stale = PortfolioManager._are_rates_stale(rates)
        
        rate_key = f"{from_currency}_{to_currency}"
        
        if rate_key not in rates:
            reverse_key = f"{to_currency}_{from_currency}"
            if reverse_key in rates:
                rate = 1 / rates[reverse_key]["rate"]
                updated_at = rates[reverse_key]["updated_at"]
                source = rates[reverse_key]["source"]
            else:
                raise ApiRequestError(f"Курс {from_currency}→{to_currency} недоступен")
        else:
            rate = rates[rate_key]["rate"]
            updated_at = rates[rate_key]["updated_at"]
            source = rates[rate_key]["source"]
        
        return {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate,
            "updated_at": updated_at,
            "source": source,
            "inverse_rate": 1 / rate if rate != 0 else 0,
            "is_fresh": not is_stale
        }

    @staticmethod
    def _load_rates() -> Dict[str, Any]:
        try:
            rates_data = db.read_json("rates.json", {})
            return rates_data.get("pairs", {})
        except Exception:
            return {}

    @staticmethod
    def _are_rates_stale(rates: Dict[str, Any]) -> bool:
        if not rates:
            return True
        
        ttl_seconds = settings.get("rates_ttl_seconds", 300)
        last_refresh = rates.get("last_refresh")
        
        if not last_refresh:
            return True
        
        try:
            from datetime import datetime
            last_update = datetime.fromisoformat(last_refresh.replace('Z', '+00:00'))
            now = datetime.now()
            age = (now - last_update).total_seconds()
            return age > ttl_seconds
        except (ValueError, TypeError):
            return True