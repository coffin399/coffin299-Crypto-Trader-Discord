from .base import BaseExchange
from ..logger import setup_logger

logger = setup_logger("hyperliquid")

class Hyperliquid(BaseExchange):
    def __init__(self, config):
        super().__init__(config)
        # Hyperliquid specific init
        self.wallet = config.get('exchanges', {}).get('hyperliquid', {}).get('wallet_address')

    async def get_balance(self):
        if self.paper_mode:
            return self.paper_balance
        # TODO: Implement real Hyperliquid API
        logger.warning("Real Hyperliquid balance fetch not implemented yet.")
        return {}

    async def get_market_price(self, pair):
        # TODO: Implement real Hyperliquid API
        # Mocking for now if not paper
        return 100.0

    async def get_ohlcv(self, pair, timeframe, limit=100):
        # TODO: Implement real Hyperliquid API
        return []

    async def _execute_real_order(self, pair, type, side, amount, price=None):
        logger.error("Real trading on Hyperliquid not implemented yet.")
        return None
