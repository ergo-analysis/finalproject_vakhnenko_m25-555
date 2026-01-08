import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from ..decorators import log_action
from .models import User, Portfolio, Wallet
from .currencies import get_currency
from .exceptions import (
    CurrencyNotFoundError, InsufficientFundsError, 
    UserNotFoundError, InvalidPasswordError, ApiRequestError
)
from ..infra.settings import settings
from ..infra.database import db
from .utils import (
    load_users, save_users, load_portfolios, save_portfolios,
    generate_salt, hash_password, get_next_user_id, find_user_by_username,
    get_user_portfolio
)


class UserManager:
    @staticmethod
    @log_action("REGISTER")
    def register(username: str, password: str) -> str:
        if find_user_by_username(username):
            raise ValueError(f"Имя пользователя '{username}' уже занято")
        
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        
        user_id = get_next_user_id()
        salt = generate_salt()
        hashed_pw = hash_password(password, salt)
        
        user = User(
            user_id=user_id,
            username=username,
            hashed_password=hashed_pw,
            salt=salt,
            registration_date=datetime.now()
        )
        
        users = load_users()
        users.append(user.to_dict())
        save_users(users)
        
        portfolio = Portfolio(user_id)
        portfolios = load_portfolios()
        portfolios.append(portfolio.to_dict())
        save_portfolios(portfolios)
        
        return f"Пользователь '{username}' зарегистрирован (id={user_id})."

    @staticmethod
    @log_action("LOGIN")
    def login(username: str, password: str) -> tuple[int, str]:
        user_data = find_user_by_username(username)
        if not user_data:
            raise UserNotFoundError(username)
        
        user = User.from_dict(user_data)
        if not user.verify_password(password):
            raise InvalidPasswordError()
        
        return user.user_id, f"Вы вошли как '{username}'"


class PortfolioManager:
    @staticmethod
    def get_portfolio_info(user_id: int, base_currency: str = "USD") -> Dict[str, Any]:
        try:
            get_currency(base_currency)
        except CurrencyNotFoundError:
            raise CurrencyNotFoundError(base_currency)
        
        portfolio_data = get_user_portfolio(user_id)
        if not portfolio_data:
            portfolio = Portfolio(user_id)
        else:
            portfolio = Portfolio.from_dict(portfolio_data)
        
        rates = PortfolioManager._load_rates()
        result = {
            "wallets": [],
            "total_value": 0.0,
            "base_currency": base_currency
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
        
        portfolio_data = get_user_portfolio(user_id)
        if not portfolio_data:
            portfolio = Portfolio(user_id)
        else:
            portfolio = Portfolio.from_dict(portfolio_data)
        
        rates = PortfolioManager._load_rates()
        rate_key = f"{currency_code}_USD"
        if rate_key not in rates:
            raise ApiRequestError(f"Не удалось получить курс для {currency_code}→USD")
        
        rate = rates[rate_key]["rate"]
        cost_usd = amount * rate
        
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet or usd_wallet.balance < cost_usd:
            raise InsufficientFundsError(
                available=usd_wallet.balance if usd_wallet else 0.0,
                required=cost_usd,
                code="USD"
            )
        
        # Сохраняем старые балансы для лога
        old_usd_balance = usd_wallet.balance
        target_wallet = portfolio.get_wallet(currency_code)
        old_target_balance = target_wallet.balance if target_wallet else 0.0
        
        # Выполняем операции
        usd_wallet.withdraw(cost_usd)
        
        if not target_wallet:
            portfolio.add_currency(currency_code)
            target_wallet = portfolio.get_wallet(currency_code)
        
        target_wallet.deposit(amount)
        
        # Сохраняем изменения
        portfolios = load_portfolios()
        for i, p in enumerate(portfolios):
            if p["user_id"] == user_id:
                portfolios[i] = portfolio.to_dict()
                break
        else:
            portfolios.append(portfolio.to_dict())
        
        save_portfolios(portfolios)
        
        # Возвращаем данные для лога и CLI
        return {
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
        
        portfolio_data = get_user_portfolio(user_id)
        if not portfolio_data:
            portfolio = Portfolio(user_id)
        else:
            portfolio = Portfolio.from_dict(portfolio_data)
        
        target_wallet = portfolio.get_wallet(currency_code)
        if not target_wallet:
            raise ValueError(f"У вас нет кошелька '{currency_code}'.")
        
        if target_wallet.balance < amount:
            raise InsufficientFundsError(
                available=target_wallet.balance,
                required=amount,
                code=currency_code
            )
        
        rates = PortfolioManager._load_rates()
        rate_key = f"{currency_code}_USD"
        if rate_key not in rates:
            raise ApiRequestError(f"Не удалось получить курс для {currency_code}→USD")
        
        rate = rates[rate_key]["rate"]
        revenue_usd = amount * rate
        
        # Сохраняем старые балансы для лога
        old_target_balance = target_wallet.balance
        usd_wallet = portfolio.get_wallet("USD")
        old_usd_balance = usd_wallet.balance if usd_wallet else 0.0
        
        # Выполняем операции
        target_wallet.withdraw(amount)
        
        if not usd_wallet:
            portfolio.add_currency("USD")
            usd_wallet = portfolio.get_wallet("USD")
        
        usd_wallet.deposit(revenue_usd)
        
        # Сохраняем изменения
        portfolios = load_portfolios()
        for i, p in enumerate(portfolios):
            if p["user_id"] == user_id:
                portfolios[i] = portfolio.to_dict()
                break
        else:
            portfolios.append(portfolio.to_dict())
        
        save_portfolios(portfolios)

        # Возвращаем данные для лога и CLI
        return {
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
        rate_key = f"{from_currency}_{to_currency}"
        
        if rate_key not in rates:
            reverse_key = f"{to_currency}_{from_currency}"
            if reverse_key in rates:
                rate = 1 / rates[reverse_key]["rate"]
                updated_at = rates[reverse_key]["updated_at"]
                source = rates[reverse_key]["source"]
            else:
                raise ValueError(f"Курс {from_currency}→{to_currency} недоступен.")
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
            "inverse_rate": 1 / rate if rate != 0 else 0
        }

    @staticmethod
    def _load_rates() -> Dict[str, Any]:
        try:
            with open("data/rates.json", "r") as f:
                data = json.load(f)
                return data.get("pairs", {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}