import ccxt.async_support as ccxt
import pandas as pd
import logging
import asyncio

class BinanceClient:
    def __init__(self, api_key, api_secret, testnet=False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.exchange = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        self.exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
        if self.testnet:
            self.exchange.set_sandbox_mode(True)
        # Load markets
        await self.exchange.load_markets()

    async def close(self):
        if self.exchange:
            await self.exchange.close()

    async def get_balance(self, currency):
        try:
            balance = await self.exchange.fetch_balance()
            return balance['total'].get(currency, 0.0), balance['free'].get(currency, 0.0)
        except Exception as e:
            self.logger.error(f"Error fetching balance for {currency}: {e}")
            return 0.0, 0.0

    async def get_ohlcv(self, symbol, timeframe='1m', limit=100):
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            self.logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    async def get_ticker(self, symbol):
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            self.logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None

    async def create_order(self, symbol, side, amount, price=None):
        try:
            if price:
                order = await self.exchange.create_order(symbol, 'limit', side, amount, price)
            else:
                order = await self.exchange.create_order(symbol, 'market', side, amount)
            return order
        except Exception as e:
            self.logger.error(f"Error creating {side} order for {symbol}: {e}")
            return None
