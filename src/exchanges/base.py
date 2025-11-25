from abc import ABC, abstractmethod
from ..logger import setup_logger
import time

logger = setup_logger("exchange_base")

class BaseExchange(ABC):
    def __init__(self, config):
        self.config = config
        self.paper_mode = config.get('strategy', {}).get('paper_mode', {}).get('enabled', False)
        self.paper_balance = config.get('strategy', {}).get('paper_mode', {}).get('initial_balance', {})
        self.positions = {} # {pair: {amount: float, entry_price: float}}
        
        if self.paper_mode:
            logger.info("Initialized in PAPER MODE")
            logger.info(f"Initial Paper Balance: {self.paper_balance}")

    @abstractmethod
    async def get_balance(self):
        pass

    @abstractmethod
    async def get_market_price(self, pair):
        pass

    @abstractmethod
    async def get_ohlcv(self, pair, timeframe, limit=100):
        pass

    async def create_order(self, pair, type, side, amount, price=None):
        if self.paper_mode:
            return await self._execute_paper_order(pair, type, side, amount, price)
        else:
            return await self._execute_real_order(pair, type, side, amount, price)

    @abstractmethod
    async def _execute_real_order(self, pair, type, side, amount, price=None):
        pass

    async def _execute_paper_order(self, pair, type, side, amount, price=None):
        logger.info(f"PAPER ORDER: {side} {amount} {pair} @ {price}")
        
        if not price:
            price = await self.get_market_price(pair)
            
        base, quote = pair.split('/')
        cost = amount * price
        
        if side == 'buy':
            if self.paper_balance.get(quote, 0) >= cost:
                self.paper_balance[quote] -= cost
                self.paper_balance[base] = self.paper_balance.get(base, 0) + amount
                
                # Track position
                current_pos = self.positions.get(pair, {'amount': 0, 'entry_price': 0})
                total_amt = current_pos['amount'] + amount
                avg_price = ((current_pos['amount'] * current_pos['entry_price']) + cost) / total_amt
                self.positions[pair] = {'amount': total_amt, 'entry_price': avg_price}
                
                return {'id': f'paper_{int(time.time())}', 'status': 'closed', 'filled': amount, 'price': price}
            else:
                logger.warning("Paper Mode: Insufficient funds")
                return None
                
        elif side == 'sell':
            if self.paper_balance.get(base, 0) >= amount:
                self.paper_balance[base] -= amount
                self.paper_balance[quote] = self.paper_balance.get(quote, 0) + cost
                
                # Update position
                current_pos = self.positions.get(pair, {'amount': 0, 'entry_price': 0})
                new_amt = current_pos['amount'] - amount
                if new_amt <= 0:
                    if pair in self.positions: del self.positions[pair]
                else:
                    self.positions[pair]['amount'] = new_amt
                    
                return {'id': f'paper_{int(time.time())}', 'status': 'closed', 'filled': amount, 'price': price}
            else:
                logger.warning("Paper Mode: Insufficient asset")
                return None
