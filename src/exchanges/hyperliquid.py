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
        # Fix: Read from 'hyperliquid' section, not 'trade_xyz'
        hl_config = config.get('exchanges', {}).get('hyperliquid', {})
        self.wallet_address = hl_config.get('wallet_address')
        self.private_key = hl_config.get('private_key')
        self.testnet = hl_config.get('testnet', False)
        
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
            # Auto-convert ETH to USDC for paper trading if USDC is low/zero but ETH exists
            # This simulates "using ETH as collateral" or "selling ETH for USDC"
            eth_bal = self.paper_balance.get('ETH', 0)
            usdc_bal = self.paper_balance.get('USDC', 0)
            
            if eth_bal > 0 and usdc_bal < 100: # Threshold
                price = 3000 # Mock price or fetch
                try:
                    price = await self.get_market_price("ETH/USDC") or 3000
                except:
                    pass
                    
                conv_val = eth_bal * price
                self.paper_balance['ETH'] = 0
                self.paper_balance['USDC'] = usdc_bal + conv_val
                logger.info(f"Paper Mode: Converted {eth_bal} ETH to {conv_val:.2f} USDC for trading.")
                
                self.paper_balance['USDC'] = usdc_bal + conv_val
                logger.info(f"Paper Mode: Converted {eth_bal} ETH to {conv_val:.2f} USDC for trading.")
                
            # Return standard structure matching real mode
            return {
                'total': {'USDC': self.paper_balance.get('USDC', 0)},
                'free': {'USDC': self.paper_balance.get('USDC', 0)},
                'used': {'USDC': 0.0} # Simplified
            }
        
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
            # Convert BaseExchange positions dict to list format
            # BaseExchange: {pair: {amount: float, entry_price: float}}
            # Expected: [{'symbol': 'ETH', 'size': 1.0, 'entry_price': 3000, 'pnl': 50, 'side': 'LONG'}]
            
            formatted_positions = []
            for pair, pos in self.positions.items():
                symbol = pair.split('/')[0]
                size = pos['amount']
                if size == 0: continue
                
                # Calculate PnL roughly
                current_price = await self.get_market_price(pair)
                entry_price = pos['entry_price']
                pnl = (current_price - entry_price) * size # Simple spot PnL
                
                formatted_positions.append({
                    'symbol': symbol,
                    'size': size,
                    'side': 'LONG', # BaseExchange paper logic is spot-like (LONG only)
                    'entry_price': entry_price,
                    'pnl': pnl
                })
            return formatted_positions
            
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
        # Use CCXT for standardized data fetching
        try:
            import ccxt.async_support as ccxt
            
            if not hasattr(self, 'ccxt_client'):
                self.ccxt_client = ccxt.hyperliquid({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'future'}
                })
                # If we have keys, we could set them, but for public data it's not needed.
                # self.ccxt_client.apiKey = ...
            
            # Map timeframe if needed (CCXT standard is usually fine)
            
            # Fetch
            # CCXT handles pagination if we loop, but here we fetch one batch.
            # The caller (strategy) handles the loop.
            
            ohlcv = await self.ccxt_client.fetch_ohlcv(pair, timeframe, since, limit)
            
            # CCXT returns [timestamp, open, high, low, close, volume]
            return ohlcv
            
        except Exception as e:
            logger.error(f"CCXT Fetch Failed: {e}")
            # Fallback to SDK if CCXT fails?
            # For now, just return empty to trigger retry or error
            return []
            
    async def close(self):
        if hasattr(self, 'ccxt_client'):
            await self.ccxt_client.close()

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
    async def get_leaderboard_top_traders(self, limit=5):
        """
        Fetches top traders from Hyperliquid stats API.
        """
        import aiohttp
        url = "https://api.hyperliquid.xyz/info"
        payload = {"type": "leaderboard", "window": "7d"} # 7d window for active traders
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        # data is list of [address, pnl, ...]
                        # We want top N addresses
                        top_traders = []
                        for row in data[:limit]:
                            # row structure depends on API. Usually row[0] is address?
                            # Let's assume row structure based on common knowledge or try to parse dict if it is dict.
                            # Actually leaderboard rows are often dicts in Hyperliquid API: {'ethAddress': '...', 'accountValue': ...}
                            if isinstance(row, dict):
                                address = row.get('ethAddress') or row.get('address')
                                if address:
                                    top_traders.append(address)
                            elif isinstance(row, list):
                                top_traders.append(row[0]) # Fallback
                        return top_traders
                    else:
                        logger.error(f"Failed to fetch leaderboard: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching leaderboard: {e}")
            return []

    async def get_user_positions(self, address):
        """
        Fetches open positions for a specific user address.
        """
        try:
            # Use SDK info.user_state(address)
            user_state = self.info.user_state(address)
            raw_positions = user_state.get('assetPositions', [])
            
            positions = []
            for p in raw_positions:
                pos = p.get('position', {})
                size = float(pos.get('szi', 0))
                if size == 0: continue
                
                symbol = pos.get('coin', 'Unknown')
                side = 'LONG' if size > 0 else 'SHORT'
                
                positions.append({
                    'symbol': symbol,
                    'side': side,
                    'size': abs(size)
                })
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch positions for {address}: {e}")
            return []
