from datetime import datetime
from typing import Any, Dict

import requests

from ..core.exceptions import ApiRequestError
from .config import ParserConfig


class BaseApiClient:
    """Базовый класс для API клиентов"""
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.response_time_ms = 0
        self.status_code = 0
        self.etag = ""
    
    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        """Получает курсы валют и возвращает с метаданными"""
        raise NotImplementedError
    
    def _log_request_info(self, response: requests.Response):
        """Логирует информацию о запросе"""
        self.response_time_ms = int(response.elapsed.total_seconds() * 1000)
        self.status_code = response.status_code
        self.etag = response.headers.get('ETag', '')


class CoinGeckoClient(BaseApiClient):
    """Клиент для CoinGecko API"""
    
    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        """Получает курсы криптовалют"""
        crypto_ids = [self.config.CRYPTO_ID_MAP[code] for code in self.config.CRYPTO_CURRENCIES]
        ids_param = ",".join(crypto_ids)
        
        url = f"{self.config.COINGECKO_URL}"
        params = {
            "ids": ids_param,
            "vs_currencies": "usd"
        }
        
        try:
            response = requests.get(
                url, 
                params=params, 
                timeout=self.config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            self._log_request_info(response)
            data = response.json()
            
            rates = {}
            timestamp = datetime.now().isoformat() + "Z"
            
            for code in self.config.CRYPTO_CURRENCIES:
                coin_id = self.config.CRYPTO_ID_MAP[code]
                if coin_id in data and "usd" in data[coin_id]:
                    rate_key = f"{code}_USD"
                    rates[rate_key] = {
                        "rate": float(data[coin_id]["usd"]),
                        "timestamp": timestamp,
                        "source": "CoinGecko",
                        "meta": {
                            "raw_id": coin_id,
                            "request_ms": self.response_time_ms,
                            "status_code": self.status_code,
                            "etag": self.etag
                        }
                    }
            
            return rates
            
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"CoinGecko API error: {e}")


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для ExchangeRate-API"""
    
    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        """Получает курсы фиатных валют"""
        url = f"{self.config.EXCHANGERATE_API_URL}/{self.config.EXCHANGERATE_API_KEY}/latest/{self.config.BASE_FIAT_CURRENCY}"
        
        try:
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            self._log_request_info(response)
            data = response.json()
            
            if data.get("result") != "success":
                raise ApiRequestError(f"ExchangeRate-API error: {data.get('error-type', 'Unknown error')}")
            
            rates = {}
            # Преобразуем время в ISO
            timestamp_raw = data.get("time_last_update_utc", "")
            try:
                dt = datetime.strptime(timestamp_raw, "%a, %d %b %Y %H:%M:%S %z")
                timestamp = dt.isoformat()
            except (ValueError, TypeError):
                timestamp = datetime.now().isoformat() + "Z"
            
            conversion_rates = data.get("conversion_rates", {})
            
            for target_currency in self.config.FIAT_CURRENCIES:
                if target_currency in conversion_rates:
                    rate_key = f"{target_currency}_{self.config.BASE_FIAT_CURRENCY}"
                    # Конвертируем курс 
                    rate = 1 / float(conversion_rates[target_currency])
                    rates[rate_key] = {
                        "rate": rate,
                        "timestamp": timestamp,
                        "source": "ExchangeRate-API",
                        "meta": {
                            "raw_data": f"1 USD = {conversion_rates[target_currency]} {target_currency}",
                            "request_ms": self.response_time_ms,
                            "status_code": self.status_code,
                            "etag": self.etag,
                            "time_next_update": data.get("time_next_update_utc", "")
                        }
                    }
            
            return rates
            
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"ExchangeRate-API error: {e}")