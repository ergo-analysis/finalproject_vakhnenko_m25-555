import json
from datetime import datetime
from typing import Optional, Dict, Any
from .models import User, Portfolio, Wallet
from .utils import (
    load_users, save_users, load_portfolios, save_portfolios,
    generate_salt, hash_password, get_next_user_id, find_user_by_username,
    get_user_portfolio
)


class UserManager:
    @staticmethod
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
        
        return f"Пользователь '{username}' зарегистрирован (id={user_id}). Войдите: login --username {username} --password ****"

    @staticmethod
    def login(username: str, password: str) -> tuple[int, str]:
        user_data = find_user_by_username(username)
        if not user_data:
            raise ValueError(f"Пользователь '{username}' не найден")
        
        user = User.from_dict(user_data)
        if not user.verify_password(password):
            raise ValueError("Неверный пароль")
        
        return user.user_id, f"Вы вошли как '{username}'"


class PortfolioManager:
    @staticmethod
    def get_portfolio_info(user_id: int, base_currency: str = "USD") -> Dict[str, Any]:
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
            value = 0.0
            if wallet.currency_code == base_currency:
                value = wallet.balance
            else:
                rate_key = f"{wallet.currency_code}_{base_currency}"
                if rate_key in rates:
                    rate = rates[rate_key]["rate"]
                    value = wallet.balance * rate
                else:
                    # Пробуем обратный курс
                    reverse_key = f"{base_currency}_{wallet.currency_code}"
                    if reverse_key in rates:
                        rate = 1 / rates[reverse_key]["rate"]
                        value = wallet.balance * rate
            
            result["wallets"].append({
                "currency": wallet.currency_code,
                "balance": wallet.balance,
                "value_in_base": value
            })
            total += value
        
        result["total_value"] = total
        return result

    @staticmethod
    def buy_currency(user_id: int, currency_code: str, amount: float) -> str:
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        
        portfolio_data = get_user_portfolio(user_id)
        if not portfolio_data:
            portfolio = Portfolio(user_id)
        else:
            portfolio = Portfolio.from_dict(portfolio_data)
        
        rates = PortfolioManager._load_rates()
        rate_key = f"{currency_code}_USD"
        if rate_key not in rates:
            raise ValueError(f"Не удалось получить курс для {currency_code}→USD")
        
        rate = rates[rate_key]["rate"]
        cost_usd = amount * rate
        
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet or usd_wallet.balance < cost_usd:
            raise ValueError(f"Недостаточно средств на USD кошельке. Требуется: {cost_usd:.2f} USD")
        
        usd_wallet.withdraw(cost_usd)
        
        target_wallet = portfolio.get_wallet(currency_code)
        if not target_wallet:
            portfolio.add_currency(currency_code)
            target_wallet = portfolio.get_wallet(currency_code)
        
        target_wallet.deposit(amount)
        
        portfolios = load_portfolios()
        for i, p in enumerate(portfolios):
            if p["user_id"] == user_id:
                portfolios[i] = portfolio.to_dict()
                break
        else:
            portfolios.append(portfolio.to_dict())
        
        save_portfolios(portfolios)
        
        return (f"Покупка выполнена: {amount:.4f} {currency_code} по курсу {rate:.2f} USD/{currency_code}\n"
                f"Изменения в портфеле:\n"
                f"- {currency_code}: было {target_wallet.balance - amount:.4f} → стало {target_wallet.balance:.4f}\n"
                f"Оценочная стоимость покупки: {cost_usd:.2f} USD")

    @staticmethod
    def sell_currency(user_id: int, currency_code: str, amount: float) -> str:
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        
        portfolio_data = get_user_portfolio(user_id)
        if not portfolio_data:
            portfolio = Portfolio(user_id)
        else:
            portfolio = Portfolio.from_dict(portfolio_data)
        
        target_wallet = portfolio.get_wallet(currency_code)
        if not target_wallet:
            raise ValueError(f"У вас нет кошелька '{currency_code}'. "
                           f"Добавьте валюту: она создаётся автоматически при первой покупке.")
        
        if target_wallet.balance < amount:
            raise ValueError(f"Недостаточно средств: доступно {target_wallet.balance:.4f} {currency_code}, "
                           f"требуется {amount:.4f} {currency_code}")
        
        rates = PortfolioManager._load_rates()
        rate_key = f"{currency_code}_USD"
        if rate_key not in rates:
            raise ValueError(f"Не удалось получить курс для {currency_code}→USD")
        
        rate = rates[rate_key]["rate"]
        revenue_usd = amount * rate
        
        target_wallet.withdraw(amount)
        
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet:
            portfolio.add_currency("USD")
            usd_wallet = portfolio.get_wallet("USD")
        
        usd_wallet.deposit(revenue_usd)
        
        portfolios = load_portfolios()
        for i, p in enumerate(portfolios):
            if p["user_id"] == user_id:
                portfolios[i] = portfolio.to_dict()
                break
        else:
            portfolios.append(portfolio.to_dict())
        
        save_portfolios(portfolios)
        
        return (f"Продажа выполнена: {amount:.4f} {currency_code} по курсу {rate:.2f} USD/{currency_code}\n"
                f"Изменения в портфеле:\n"
                f"- {currency_code}: было {target_wallet.balance + amount:.4f} → стало {target_wallet.balance:.4f}\n"
                f"Оценочная выручка: {revenue_usd:.2f} USD")

    @staticmethod
    def get_exchange_rate(from_currency: str, to_currency: str) -> Dict[str, Any]:
        if not from_currency or not to_currency:
            raise ValueError("Коды валют не могут быть пустыми")
        
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        rates = PortfolioManager._load_rates()
        rate_key = f"{from_currency}_{to_currency}"
        
        if rate_key not in rates:
            reverse_key = f"{to_currency}_{from_currency}"
            if reverse_key in rates:
                rate = 1 / rates[reverse_key]["rate"]
                updated_at = rates[reverse_key]["updated_at"]
                source = rates[reverse_key]["source"]
            else:
                raise ValueError(f"Курс {from_currency}→{to_currency} недоступен. Повторите попытку позже.")
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