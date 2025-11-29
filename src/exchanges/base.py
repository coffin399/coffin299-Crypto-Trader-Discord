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
            
            
            # Load positions from DB
            from ..database import PositionDB
            self.db = PositionDB()
            loaded_positions = self.db.load_positions()
            if loaded_positions:
                # ❌ サイズが0のポジションを除外（クローズ済みのデータが残っている場合に対応）
                self.positions = {pair: pos for pair, pos in loaded_positions.items() if pos.get('amount', 0) != 0}
                logger.info(f"Loaded {len(self.positions)} paper positions from DB (filtered out zero-size positions).")

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
            # Futures Buy: Increases position size (Long) or Decreases Short
            # Cost is margin, but for simple paper mode we just track PnL or assume sufficient margin if balance > 0
            
            # Simplified: Just check if we have some quote currency (USDC)
            if self.paper_balance.get(quote, 0) > 0:
                # Update position
                current_pos = self.positions.get(pair, {'amount': 0, 'entry_price': 0})
                old_amt = current_pos['amount']
                new_amt = old_amt + amount
                
                # Calculate new entry price if increasing position
                if old_amt >= 0:
                    cost = amount * price
                    total_cost = (old_amt * current_pos['entry_price']) + cost
                    avg_price = total_cost / new_amt if new_amt != 0 else 0
                    self.positions[pair] = {'amount': new_amt, 'entry_price': avg_price}
                else:
                    # ショート(売り)ポジションをクローズ中
                    # 実現損益ロジックをここに追加予定
                    self.positions[pair]['amount'] = new_amt
                    # DBに保存してからポジションを削除
                    if hasattr(self, 'db'):
                        if new_amt == 0:
                            # ポジションが完全にクローズされた場合、amount=0としてDB保存（自動削除される）
                            self.db.save_position(pair, 0, 0)
                            del self.positions[pair]
                        else:
                            # 部分的にクローズされた場合、新しいサイズを保存
                            self.db.save_position(pair, new_amt, self.positions[pair]['entry_price'])
                    else:
                        # DBがない場合でも削除処理を実行
                        if new_amt == 0:
                            del self.positions[pair]

                return {'id': f'paper_{int(time.time())}', 'status': 'closed', 'filled': amount, 'price': price}
            else:
                logger.warning("Paper Mode: Insufficient funds (Balance <= 0)")
                return None
                
        elif side == 'sell':
            # Futures Sell: Decreases Long or Increases Short (Negative amount)
            
            if self.paper_balance.get(quote, 0) > 0:
                # Update position
                current_pos = self.positions.get(pair, {'amount': 0, 'entry_price': 0})
                old_amt = current_pos['amount']
                new_amt = old_amt - amount
                
                # Calculate new entry price if increasing short (becoming more negative)
                if old_amt <= 0:
                    cost = amount * price
                    total_cost = (abs(old_amt) * current_pos['entry_price']) + cost
                    avg_price = total_cost / abs(new_amt) if new_amt != 0 else 0
                    self.positions[pair] = {'amount': new_amt, 'entry_price': avg_price}
                else:
                    # ロング(買い)ポジションをクローズ中
                    self.positions[pair]['amount'] = new_amt
                    # DBに保存してからポジションを削除
                    if hasattr(self, 'db'):
                        if new_amt == 0:
                            # ポジションが完全にクローズされた場合、amount=0としてDB保存（自動削除される）
                            self.db.save_position(pair, 0, 0)
                            del self.positions[pair]
                        else:
                            # 部分的にクローズされた場合、新しいサイズを保存
                            self.db.save_position(pair, new_amt, self.positions[pair]['entry_price'])
                    else:
                        # DBがない場合でも削除処理を実行
                        if new_amt == 0:
                            del self.positions[pair]

                return {'id': f'paper_{int(time.time())}', 'status': 'closed', 'filled': amount, 'price': price}
            else:
                logger.warning("Paper Mode: Insufficient funds (Balance <= 0)")
                return None
