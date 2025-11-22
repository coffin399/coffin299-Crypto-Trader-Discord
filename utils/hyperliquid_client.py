import ccxt.async_support as ccxt
import pandas as pd
import logging
import asyncio

class HyperliquidClient:
    def __init__(self, wallet_address, wallet_private_key, testnet=False, paper_trading=False, paper_initial_usd=10000):
        self.wallet_address = wallet_address
        self.wallet_private_key = wallet_private_key
        self.testnet = testnet
        self.paper_trading = paper_trading
        self.paper_initial_usd = paper_initial_usd
        self.exchange = None
        self.logger = logging.getLogger(__name__)
        
        # Paper Trading State
        self.paper_balances = {}
        self.paper_positions = {} # Symbol -> {entry_price, size, side}

    async def initialize(self):
        self.exchange = ccxt.hyperliquid({
            'walletAddress': self.wallet_address,
            'privateKey': self.wallet_private_key,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap', # Perpetuals
            }
        })
        if self.testnet:
            self.exchange.set_sandbox_mode(True)
        
        # Load markets
        try:
            await self.exchange.load_markets()
        except Exception as e:
            self.logger.error(f"Error loading markets: {e}")

        if self.paper_trading:
            await self._init_paper_balances()

    async def _init_paper_balances(self):
        self.paper_balances = {'USDC': {'free': self.paper_initial_usd, 'total': self.paper_initial_usd}}
        self.logger.info(f"[PAPER] Initialized balances with ${self.paper_initial_usd:.2f} USDC")

    async def close(self):
        if self.exchange:
            await self.exchange.close()

    async def get_balance_usdc(self):
        """Returns (total, free) USDC balance"""
        if self.paper_trading:
            bal = self.paper_balances.get('USDC', {'free': 0.0, 'total': 0.0})
            return bal['total'], bal['free']
        
        try:
            balance = await self.exchange.fetch_balance()
            # Hyperliquid usually settles in USDC
            return balance['total'].get('USDC', 0.0), balance['free'].get('USDC', 0.0)
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            return 0.0, 0.0

    async def get_position(self, symbol):
        """Returns position dict or None"""
        if self.paper_trading:
            return self.paper_positions.get(symbol)
        
        try:
            positions = await self.exchange.fetch_positions([symbol])
            # CCXT returns a list of positions. Find the one for our symbol.
            for pos in positions:
                if pos['symbol'] == symbol and pos['contracts'] > 0:
                    return pos
            return None
        except Exception as e:
            self.logger.error(f"Error fetching position for {symbol}: {e}")
            return None

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

    async def create_order(self, symbol, side, amount, price=None, params={}):
        if self.paper_trading:
            return await self._create_paper_order(symbol, side, amount, price)

        try:
            # Hyperliquid specific: ensure we are sending correct params for leverage if needed
            # For now, assume market/limit orders
            type = 'limit' if price else 'market'
            order = await self.exchange.create_order(symbol, type, side, amount, price, params)
            return order
        except Exception as e:
            self.logger.error(f"Error creating {side} order for {symbol}: {e}")
            return None

    async def _create_paper_order(self, symbol, side, amount, price=None):
        # Simple Paper Execution for Perpetuals
        if not price:
            ticker = await self.get_ticker(symbol)
            if not ticker: return None
            price = ticker['last']

        cost = amount * price
        # Simplified margin check (1x leverage for paper)
        
        if side.upper() == 'BUY':
            # Long
            # In paper mode for perps, we just track the position
            # For simplicity, let's just track net position size
            current_pos = self.paper_positions.get(symbol, {'size': 0.0, 'entry_price': 0.0, 'side': 'NONE'})
            
            new_size = current_pos['size'] + amount
            # Update weighted average entry price
            total_cost = (current_pos['size'] * current_pos['entry_price']) + (amount * price)
            new_entry = total_cost / new_size if new_size > 0 else 0
            
            self.paper_positions[symbol] = {
                'size': new_size,
                'entry_price': new_entry,
                'side': 'LONG' # Simplified
            }
            
        elif side.upper() == 'SELL':
            # Short or Close Long
            # For simplicity in this paper mode, we treat SELL as reducing Long or opening Short
            # But let's just assume we are closing/reducing for now or flipping
            # This is complex to mock perfectly without a full engine.
            # Let's just log it and update "size"
            current_pos = self.paper_positions.get(symbol, {'size': 0.0, 'entry_price': 0.0, 'side': 'NONE'})
            new_size = current_pos['size'] - amount
            
            self.paper_positions[symbol] = {
                'size': new_size,
                'entry_price': current_pos['entry_price'], # Entry price doesn't change on reduction
                'side': 'LONG' if new_size > 0 else 'SHORT' if new_size < 0 else 'NONE'
            }

        self.logger.info(f"[PAPER] Executed {side} {amount} {symbol} @ {price}")
        return {'id': 'paper_order', 'symbol': symbol, 'side': side, 'amount': amount, 'price': price}
