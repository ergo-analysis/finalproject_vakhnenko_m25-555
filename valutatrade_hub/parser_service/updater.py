from datetime import datetime
from typing import Any, Dict

from ..core.exceptions import ApiRequestError
from ..logging_config import get_logger
from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .config import ParserConfig
from .storage import RatesStorage


class RatesUpdater:
    """Основной класс для обновления курсов валют"""
    
    def __init__(self, config: ParserConfig = None):
        self.config = config or ParserConfig()
        self.storage = RatesStorage(self.config)

        
        # файловый логгер для технических записей
        self.rates_logger = get_logger("rates_operations")
        
        self.coingecko_client = CoinGeckoClient(self.config)
        self.exchangerate_client = ExchangeRateApiClient(self.config)
    
    def run_update(self, source: str = None) -> Dict[str, Any]:
        """Запускает обновление курсов"""
        source = source.lower() if source else None
        self.rates_logger.info(f"UPDATE_RATES action=START source={source or 'all'}")
        
        all_rates = {}
        errors = []
        
        try:
            # тут крипта от CoinGecko
            if source in [None, "coingecko", "crypto"]:
                self.rates_logger.info("FETCH_CRYPTO action=START")
                try:
                    crypto_rates = self.coingecko_client.fetch_rates()
                    all_rates.update(crypto_rates)
                    
                    self.rates_logger.info("FETCH_CRYPTO action=SUCCESS")
                except ApiRequestError as e:
                    errors.append(f"CoinGecko: {e.reason}")
                   
                    self.rates_logger.info("FETCH_CRYPTO action=ERROR")
            

            if source in [None, "exchangerate", "fiat"]:
                self.rates_logger.info("FETCH_FIAT action=START")
                try:
                    fiat_rates = self.exchangerate_client.fetch_rates()
                    all_rates.update(fiat_rates)
 
                    self.rates_logger.info("FETCH_FIAT action=SUCCESS")
                except ApiRequestError as e:
                    errors.append(f"ExchangeRate-API: {e.reason}")
                    self.rates_logger.info("FETCH_FIAT action=ERROR")
            
            # Сохраняем результаты
            if all_rates:
                self.storage.save_current_rates(all_rates)
                self.storage.update_history_from_rates(all_rates)
                
                result = {
                    "success": True,
                    "rates_count": len(all_rates),
                    "last_refresh": datetime.now().isoformat() + "Z",
                    "errors": errors if errors else None
                }
                
                self.rates_logger.info(f"UPDATE_RATES action=SUCCESS rates_count={len(all_rates)}")
                return result
            else:
                self.rates_logger.info("UPDATE_RATES action=ERROR reason='No rates fetched'")
                raise ApiRequestError("No rates were fetched from any source")
                
        except Exception:
            self.rates_logger.info("UPDATE_RATES action=ERROR")
            raise