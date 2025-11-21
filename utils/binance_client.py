import ccxt.async_support as ccxt
import pandas as pd
import logging
import asyncio

class BinanceClient:
    def __init__(self, api_key, api_secret, testnet=False, paper_trading=False, paper_initial_btc=0):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.paper_trading = paper_trading
        self.paper_initial_btc = paper_initial_btc
        self.exchange = None
        self.logger = logging.getLogger(__name__)
        
        # Paper Trading State
        self.paper_balances = {}

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
        try:
            await self.exchange.load_markets()
        except Exception as e:
            self.logger.error(f"Error loading markets: {e}")
            # Continue anyway, as we might not need all markets for basic trading
            # or if it's just a margin permission error

        if self.paper_trading:
            await self._init_paper_balances()

    async def _init_paper_balances(self):
        try:
            # Start with fixed BTC amount
            btc_amount = self.paper_initial_btc
            self.paper_balances = {
                'BTC': {'free': btc_amount, 'total': btc_amount},
                'ETH': {'free': 0.0, 'total': 0.0}
            }
            self.logger.info(f"[PAPER] Initialized balances with {btc_amount:.8f} BTC")
        except Exception as e:
            self.logger.error(f"Error initializing paper balances: {e}")
            # Fallback
            self.paper_balances = {'BTC': {'free': 0.0, 'total': 0.0}, 'ETH': {'free': 0.0, 'total': 0.0}}

    async def close(self):
        if self.exchange:
            await self.exchange.close()

    async def get_balance(self, currency):
        if self.paper_trading:
            bal = self.paper_balances.get(currency, {'free': 0.0, 'total': 0.0})
            return bal['total'], bal['free']
        
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
        if self.paper_trading:
            return await self._create_paper_order(symbol, side, amount, price)

        try:
            if price:
                order = await self.exchange.create_order(symbol, 'limit', side, amount, price)
            else:
                order = await self.exchange.create_order(symbol, 'market', side, amount)
            return order
        except Exception as e:
            self.logger.error(f"Error creating {side} order for {symbol}: {e}")
            return None

    async def _create_paper_order(self, symbol, side, amount, price=None):
        # Simple Paper Execution
        base, quote = symbol.split('/') # e.g. ETH/BTC -> Base: ETH, Quote: BTC
        
        # Get current price if not limit
        if not price:
            ticker = await self.get_ticker(symbol)
            if not ticker: return None
            price = ticker['last']

        cost = amount * price
        
        # Check Balance
        if side.upper() == 'BUY':
            quote_bal = self.paper_balances.get(quote, {'free': 0.0})['free']
            if quote_bal < cost:
                self.logger.warning(f"[PAPER] Insufficient {quote} for BUY. Have {quote_bal}, Need {cost}")
                return None
            
            # Execute
            self.paper_balances[quote]['free'] -= cost
            self.paper_balances[quote]['total'] -= cost
            
            base_bal = self.paper_balances.get(base, {'free': 0.0, 'total': 0.0})
            base_bal['free'] += amount
            base_bal['total'] += amount
            self.paper_balances[base] = base_bal
            
        elif side.upper() == 'SELL':
            base_bal = self.paper_balances.get(base, {'free': 0.0})['free']
            if base_bal < amount:
                self.logger.warning(f"[PAPER] Insufficient {base} for SELL. Have {base_bal}, Need {amount}")
                return None
                
            # Execute
            self.paper_balances[base]['free'] -= amount
            self.paper_balances[base]['total'] -= amount
            
            quote_bal = self.paper_balances.get(quote, {'free': 0.0, 'total': 0.0})
            quote_bal['free'] += cost
            quote_bal['total'] += cost
            self.paper_balances[quote] = quote_bal

        self.logger.info(f"[PAPER] Executed {side} {amount} {symbol} @ {price}")
        return {'id': 'paper_order', 'symbol': symbol, 'side': side, 'amount': amount, 'price': price}
