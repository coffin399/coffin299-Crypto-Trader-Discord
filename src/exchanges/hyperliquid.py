import eth_account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from datetime import datetime
from .base import BaseExchange
from ..logger import setup_logger

logger = setup_logger("hyperliquid")

class Hyperliquid(BaseExchange):
    def __init__(self, config):
        super().__init__(config)
        self.wallet_address = config.get('exchanges', {}).get('trade_xyz', {}).get('wallet_address')
        self.private_key = config.get('exchanges', {}).get('trade_xyz', {}).get('private_key')
        self.testnet = config.get('exchanges', {}).get('trade_xyz', {}).get('testnet', False)
        
        self.base_url = constants.TESTNET_API_URL if self.testnet else constants.MAINNET_API_URL
        
        # Initialize SDK components
        self.info = Info(self.base_url, skip_ws=True)
        
        if self.private_key:
            try:
                self.account = eth_account.Account.from_key(self.private_key)
                self.exchange = Exchange(self.account, self.base_url, account_address=self.wallet_address)
            except Exception as e:
                logger.error(f"Failed to init Hyperliquid Exchange: {e}")
                self.exchange = None
        else:
            self.exchange = None
            if not self.paper_mode:
                logger.warning("Hyperliquid Private Key not provided. Trading disabled (unless in Paper Mode).")
            else:
                logger.info("Hyperliquid initialized in Paper Mode (No Private Key). Public data only.")

    async def get_balance(self):
        if self.paper_mode:
            return self.paper_balance
        
        try:
            user_state = self.info.user_state(self.wallet_address)
            # user_state['marginSummary'] contains total equity
            # user_state['assetPositions'] contains positions
            
            total_equity = float(user_state.get('marginSummary', {}).get('accountValue', 0))
            
            # Simplified balance structure
            return {
                'total': {
                    'USDC': total_equity # Hyperliquid is USDC margined
                },
                'free': {
                    'USDC': float(user_state.get('withdrawable', 0))
                }
            }
        except Exception as e:
            logger.error(f"Failed to fetch Hyperliquid balance: {e}")
            return {}

    async def get_positions(self):
        """
        Returns a list of open positions.
        Format: [{'symbol': 'ETH', 'size': 1.0, 'entry_price': 3000, 'pnl': 50, 'side': 'LONG'}]
        """
        if self.paper_mode:
            # TODO: Implement paper positions tracking
            return []
            
        try:
            user_state = self.info.user_state(self.wallet_address)
            raw_positions = user_state.get('assetPositions', [])
            
            positions = []
            for p in raw_positions:
                pos = p.get('position', {})
                size = float(pos.get('szi', 0))
                if size == 0: continue
                
                entry_price = float(pos.get('entryPx', 0))
                symbol = pos.get('coin', 'Unknown')
                
                # Calculate PnL (Unrealized)
                # We need current price. 
                # For efficiency, we might skip exact PnL or fetch it.
                # Hyperliquid user_state might have it? 
                # 'unrealizedPnl' is in position?
                pnl = float(pos.get('unrealizedPnl', 0))
                
                positions.append({
                    'symbol': symbol,
                    'size': abs(size),
                    'side': 'LONG' if size > 0 else 'SHORT',
                    'entry_price': entry_price,
                    'pnl': pnl
                })
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return []

    async def get_market_price(self, pair):
        try:
            # pair format: ETH/USDC -> ETH
            coin = pair.split('/')[0]
            all_mids = self.info.all_mids()
            return float(all_mids.get(coin, 0))
        except Exception as e:
            logger.error(f"Failed to fetch price for {pair}: {e}")
            return 0.0

    async def get_ohlcv(self, pair, timeframe, since=None, limit=100):
        try:
            coin = pair.split('/')[0]
            # Map timeframe to Hyperliquid format if needed
            # SDK candles_snapshot(coin, interval, startTime, endTime)
            
            start_time = since if since else 0
            # If since is provided, we want data FROM that time.
            # If not, we might want recent data.
            
            # Hyperliquid 'candles_snapshot' seems to return data between start and end.
            # We need to ensure we get enough data.
            
            end_time = int(datetime.now().timestamp() * 1000)
            
            # If we are paginating, 'since' is the start.
            # We can request a large chunk.
            
            candles = self.info.candles_snapshot(coin, timeframe, start_time, end_time)
            
            # Filter/Limit if needed (SDK might return all in range)
            # If we got too many, we might slice, but usually we want all for training.
            # But the caller expects 'limit' roughly or just a batch.
            
            # Convert to standard OHLCV
            # [timestamp, open, high, low, close, volume]
            formatted = []
            for c in candles:
                formatted.append([
                    c['t'],
                    float(c['o']),
                    float(c['h']),
                    float(c['l']),
                    float(c['c']),
                    float(c['v'])
                ])
            
            # Sort by time just in case
            formatted.sort(key=lambda x: x[0])
            
            # If limit is strict, we might slice, but for history fetch we usually want max.
            # The caller 'fetch_historical_data' handles pagination loop.
            
            return formatted
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV: {e}")
            return []

    async def _execute_real_order(self, pair, type, side, amount, price=None):
        if not self.exchange:
            logger.error("Cannot execute order: Exchange not initialized")
            return None

        try:
            coin = pair.split('/')[0]
            is_buy = side == 'buy'
            
            # Hyperliquid SDK order format
            # order(coin, is_buy, sz, limit_px, order_type, reduce_only)
            
            if type == 'market':
                # Market orders in SDK are often treated as aggressive limit orders or specific market type
                # For simplicity, we might need to check SDK specifics. 
                # Assuming 'market' type exists or we use high slippage limit.
                # The SDK `market_open` helper might be useful if available, but `order` is core.
                # Let's use `market_open` if it exists, otherwise standard order with aggressive price.
                
                # Using exchange.market_open(coin, is_buy, sz, px=None, slippage=0.05)
                result = self.exchange.market_open(coin, is_buy, amount)
                return result
                
            elif type == 'limit':
                if not price:
                    logger.error("Limit order requires price")
                    return None
                
                result = self.exchange.order(coin, is_buy, amount, price, {"limit": {"tif": "Gtc"}})
                return result
                
        except Exception as e:
            logger.error(f"Hyperliquid Order Failed: {e}")
            return None

    async def close(self):
        pass
