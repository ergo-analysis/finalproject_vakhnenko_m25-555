import time
from datetime import datetime
from typing import Dict, Any
from .config import ParserConfig
from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .storage import RatesStorage
from ..core.exceptions import ApiRequestError
from ..logging_config import get_logger


class RatesUpdater:
    """Основной класс для обновления курсов валют"""
    
    def __init__(self, config: ParserConfig = None):
        self.config = config or ParserConfig()
        self.storage = RatesStorage(self.config)
        self.logger = get_logger("parser")
        
        #создание клиента
        self.coingecko_client = CoinGeckoClient(self.config)
        self.exchangerate_client = ExchangeRateApiClient(self.config)
    
    def run_update(self, source: str = None) -> Dict[str, Any]:
        """Запускает обновление курсов"""
        source = source.lower() if source else None
        self.logger.info(f"Starting rates update (source: {source or 'all'})")
        
        all_rates = {}
        errors = []
        
        try:
            # тут крипта от CoinGecko
            if source in [None, "coingecko", "crypto"]:
                try:
                    crypto_rates = self.coingecko_client.fetch_rates()
                    all_rates.update(crypto_rates)
                    self.logger.info(f"Fetched {len(crypto_rates)} rates from CoinGecko")
                except ApiRequestError as e:
                    errors.append(f"CoinGecko: {e.reason}")
                    self.logger.error(f"Failed to fetch from CoinGecko: {e}")
            
            #тут фиаты от ExchangeRate-API 
            if source in [None, "exchangerate", "fiat"]:
                try:
                    fiat_rates = self.exchangerate_client.fetch_rates()
                    all_rates.update(fiat_rates)
                    self.logger.info(f"Fetched {len(fiat_rates)} rates from ExchangeRate-API")
                except ApiRequestError as e:
                    errors.append(f"ExchangeRate-API: {e.reason}")
                    self.logger.error(f"Failed to fetch from ExchangeRate-API: {e}")
            
            # Сохраняем результаты
            if all_rates:
                self.storage.save_current_rates(all_rates)
                self.storage.update_history_from_rates(all_rates)
                
                self.logger.info(f"Saved {len(all_rates)} rates to storage")
                
                result = {
                    "success": True,
                    "rates_count": len(all_rates),
                    "last_refresh": datetime.now().isoformat() + "Z",
                    "errors": errors if errors else None
                }
                
                return result
            else:
                self.logger.warning("No rates were fetched")
                raise ApiRequestError("No rates were fetched from any source")
                
        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            raise