import ccxt.async_support as ccxt
from .base import BaseExchange
from ..logger import setup_logger

logger = setup_logger("trade_xyz")

class TradeXYZ(BaseExchange):
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.get('exchanges', {}).get('trade_xyz', {}).get('api_key')
        self.secret = config.get('exchanges', {}).get('trade_xyz', {}).get('api_secret')
        self.testnet = config.get('exchanges', {}).get('trade_xyz', {}).get('testnet', False)
        
        # Defaulting to Binance as the underlying engine for "trade.xyz"
        # Change 'binance' to the specific ccxt id if trade.xyz is supported
        self.exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'} # or future
        })
        self.exchange.set_sandbox_mode(self.testnet)

    async def get_balance(self):
        if self.paper_mode:
            return self.paper_balance
        return await self.exchange.fetch_balance()

    async def get_market_price(self, pair):
        ticker = await self.exchange.fetch_ticker(pair)
        return ticker['last']

    async def get_ohlcv(self, pair, timeframe, limit=100):
        return await self.exchange.fetch_ohlcv(pair, timeframe, limit=limit)

    async def _execute_real_order(self, pair, type, side, amount, price=None):
        return await self.exchange.create_order(pair, type, side, amount, price)
        
    async def close(self):
        await self.exchange.close()
