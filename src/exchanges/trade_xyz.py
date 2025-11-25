import ccxt.async_support as ccxt
from .base import BaseExchange
from ..logger import setup_logger

logger = setup_logger("trade_xyz")

class TradeXYZ(BaseExchange):
    def __init__(self, config):
        super().__init__(config)
        
        # Trade.xyz uses Hyperliquid API
        self.wallet_address = config.get('exchanges', {}).get('trade_xyz', {}).get('wallet_address')
        self.private_key = config.get('exchanges', {}).get('trade_xyz', {}).get('private_key')
        self.testnet = config.get('exchanges', {}).get('trade_xyz', {}).get('testnet', False)
        
        # Initialize CCXT Hyperliquid
        # CCXT mapping: apiKey -> walletAddress, secret -> privateKey
        self.exchange = ccxt.hyperliquid({
            'apiKey': self.wallet_address,
            'secret': self.private_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'} # Hyperliquid is primarily perps
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
