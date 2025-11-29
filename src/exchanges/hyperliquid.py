import eth_account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from datetime import datetime
import asyncio
import time
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
        
        # WebSocket data caches
        self.price_cache = {}
        self.position_cache = []
        self.balance_cache = {}
        self.last_update_time = {}
        self.ws_connected = False
        
        # Initialize Info (lightweight, for REST API fallback only)
        # WebSocket will be started separately via start_websocket()
        self.info = None
        try:
            self.info = Info(self.base_url, skip_ws=True)
            logger.info("Hyperliquid Info initialized (REST API fallback available)")
        except Exception as e:
            logger.warning(f"Failed to initialize Info (WebSocket will be primary): {e}")
        
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
                
            # Return standard structure matching real mode
            return {
                'total': {'USDC': self.paper_balance.get('USDC', 0)},
                'free': {'USDC': self.paper_balance.get('USDC', 0)},
                'used': {'USDC': 0.0} # Simplified
            }
        
        # Prefer WebSocket cache
        if self.balance_cache:
            # Check staleness
            last_update = self.last_update_time.get('balance', 0)
            if time.time() - last_update < 60:
                total_equity = self.balance_cache.get('accountValue', 0)
                withdrawable = self.balance_cache.get('withdrawable', 0)
                logger.debug(f"💰 Balance from WebSocket cache: ${total_equity:.2f}")
                return {
                    'total': {'USDC': total_equity},
                    'free': {'USDC': withdrawable},
                    'used': {'USDC': total_equity - withdrawable}
                }
            else:
                logger.warning(f"⚠️ Balance cache stale ({int(time.time() - last_update)}s old), falling back to REST")
        
        # Fallback to REST API
        try:
            if not self.info:
                # Try lazy init
                try:
                    self.info = Info(self.base_url, skip_ws=True)
                except:
                    logger.warning("Info not initialized, cannot fetch balance")
                    return {'total': {}, 'free': {}, 'used': {}}
                
            logger.debug("⚠️ Balance cache empty or stale, fetching from REST API")
            user_state = self.info.user_state(self.wallet_address)
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
            
            # Fetch all prices once to avoid rate limits
            all_prices = await self.get_all_prices()
            
            for pair, pos in self.positions.items():
                symbol = pair.split('/')[0]
                size = pos['amount']
                if size == 0: continue
                
                # Calculate PnL roughly
                current_price = all_prices.get(symbol, 0)
                if current_price == 0:
                     # Fallback if missing in bulk fetch (rare)
                     try:
                        current_price = await self.get_market_price(pair)
                     except:
                        current_price = pos['entry_price'] # Fallback to entry price (0 PnL)

                entry_price = pos['entry_price']
                pnl = (current_price - entry_price) * size # Simple spot PnL
                position_value = abs(size) * current_price
                
                formatted_positions.append({
                    'symbol': symbol,
                    'size': abs(size),
                    'side': 'LONG' if size > 0 else 'SHORT',
                    'entry_price': entry_price,
                    'mark_price': current_price,
                    'value': position_value,
                    'pnl': pnl
                })
            return formatted_positions
        
        # Prefer WebSocket cache
        if self.position_cache:
            # Check staleness (e.g. 60 seconds)
            last_update = self.last_update_time.get('positions', 0)
            if time.time() - last_update < 60:
                logger.debug(f"💼 Positions from WebSocket cache: {len(self.position_cache)} active")
                return self.position_cache
            else:
                logger.warning(f"⚠️ Position cache stale ({int(time.time() - last_update)}s old), falling back to REST")
            
        # Fallback to REST API
        try:
            if not self.info:
                # Try lazy init
                try:
                    self.info = Info(self.base_url, skip_ws=True)
                except:
                    logger.warning("Info not initialized, cannot fetch positions")
                    return []
                
            logger.debug("⚠️ Position cache empty or stale, fetching from REST API")
            user_state = self.info.user_state(self.wallet_address)
            raw_positions = user_state.get('assetPositions', [])
            
            positions = self._parse_positions(raw_positions)
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return []

    async def start_websocket(self):
        """
        Starts the WebSocket connection to listen for:
        - allMids: price updates
        - user: position, balance, and order updates (if wallet configured)
        """
        import websockets
        import json
        
        ws_url = "wss://api.hyperliquid-testnet.xyz/ws" if self.testnet else "wss://api.hyperliquid.xyz/ws"
        logger.info(f"🔵 Connecting to WebSocket: {ws_url}")
        
        while True:
            try:
                async with websockets.connect(ws_url) as websocket:
                    logger.info("✅ WebSocket Connected")
                    self.ws_connected = True
                    
                    # Subscribe to allMids (price data)
                    subscribe_allmids = {
                        "method": "subscribe",
                        "subscription": {"type": "allMids"}
                    }
                    await websocket.send(json.dumps(subscribe_allmids))
                    logger.info("📊 Subscribed to allMids")
                    
                    # Subscribe to user data (if wallet address configured)
                    if self.wallet_address and not self.paper_mode:
                        subscribe_user = {
                            "method": "subscribe",
                            "subscription": {
                                "type": "user",
                                "user": self.wallet_address
                            }
                        }
                        await websocket.send(json.dumps(subscribe_user))
                        logger.info(f"👤 Subscribed to user events for {self.wallet_address[:10]}...")
                    
                    # Message handling loop
                    while True:
                        msg = await websocket.recv()
                        data = json.loads(msg)
                        
                        channel = data.get("channel")
                        
                        # Handle price updates
                        if channel == "allMids":
                            self._handle_price_update(data)
                        
                        # Handle user events (positions, balance, fills)
                        elif channel == "user":
                            self._handle_user_event(data)
                        
                        # Handle subscription confirmations
                        elif channel == "subscriptionResponse":
                            sub_type = data.get("data", {}).get("subscription", {}).get("type")
                            logger.debug(f"✅ Subscription confirmed: {sub_type}")
                            
            except websockets.exceptions.ConnectionClosed as e:
                self.ws_connected = False
                logger.warning(f"⚠️ WebSocket connection closed: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                self.ws_connected = False
                logger.error(f"❌ WebSocket Error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
    
    def _handle_price_update(self, data):
        """Handle allMids price updates"""
        mids = data.get("data", {}).get("mids", {})
        if mids:
            for coin, price in mids.items():
                self.price_cache[coin] = float(price)
            self.last_update_time['prices'] = time.time()
            logger.debug(f"📈 Updated {len(mids)} prices")
    
    def _handle_user_event(self, data):
        """Handle user event updates (positions, balance, fills)"""
        event_data = data.get("data", {})
        
        # Update positions from assetPositions
        if "assetPositions" in event_data:
            raw_positions = event_data["assetPositions"]
            self.position_cache = self._parse_positions(raw_positions)
            self.last_update_time['positions'] = time.time()
            logger.debug(f"💼 Updated positions: {len(self.position_cache)} active")
        
        # Update balance from crossMarginSummary
        if "crossMarginSummary" in event_data:
            margin_summary = event_data["crossMarginSummary"]
            self.balance_cache = {
                'accountValue': float(margin_summary.get('accountValue', 0)),
                'totalMarginUsed': float(margin_summary.get('totalMarginUsed', 0)),
                'withdrawable': float(margin_summary.get('withdrawable', 0))
            }
            self.last_update_time['balance'] = time.time()
            logger.debug(f"💰 Updated balance: ${self.balance_cache.get('accountValue', 0):.2f}")
        
        # Log fills (trades executed)
        if "fills" in event_data:
            fills = event_data["fills"]
            for fill in fills:
                coin = fill.get("coin", "?")
                side = fill.get("side", "?")
                px = fill.get("px", 0)
                sz = fill.get("sz", 0)
                logger.info(f"✅ Fill executed: {side} {sz} {coin} @ {px}")
    
    def _parse_positions(self, raw_positions):
        """Parse raw position data into standardized format"""
        positions = []
        for p in raw_positions:
            pos = p.get('position', {})
            size = float(pos.get('szi', 0))
            if size == 0:
                continue
            
            symbol = pos.get('coin', 'Unknown')
            entry_price = float(pos.get('entryPx', 0))
            pnl = float(pos.get('unrealizedPnl', 0))
            
            # Get mark price from cache
            mark_price = self.price_cache.get(symbol, entry_price)
            position_value = abs(size) * mark_price
            
            positions.append({
                'symbol': symbol,
                'size': abs(size),
                'side': 'LONG' if size > 0 else 'SHORT',
                'entry_price': entry_price,
                'mark_price': mark_price,
                'value': position_value,
                'pnl': pnl
            })
        return positions

    async def get_market_price(self, pair):
        # Use cache if available
        if hasattr(self, 'price_cache') and self.price_cache:
            # Check staleness
            last_update = self.last_update_time.get('prices', 0)
            if time.time() - last_update < 60:
                coin = pair.split('/')[0]
                price = self.price_cache.get(coin)
                if price:
                    return price
            else:
                logger.debug(f"⚠️ Price cache stale ({int(time.time() - last_update)}s old)")
                
        # Fallback to REST
        try:
            if not self.info:
                # Try lazy init
                try:
                    self.info = Info(self.base_url, skip_ws=True)
                except:
                    logger.warning("Info not initialized, cannot fetch price")
                    return 0.0

            coin = pair.split('/')[0]
            all_mids = self.info.all_mids()
            return float(all_mids.get(coin, 0))
        except Exception as e:
            logger.error(f"Failed to fetch price for {pair}: {e}")
            return 0.0

    async def get_all_prices(self):
        """
        Fetches prices for all coins. Uses WS cache if available.
        """
        if hasattr(self, 'price_cache') and self.price_cache:
            # Check staleness
            last_update = self.last_update_time.get('prices', 0)
            if time.time() - last_update < 60:
                return self.price_cache.copy()
            else:
                logger.debug(f"⚠️ Price cache stale ({int(time.time() - last_update)}s old)")
            
        try:
            if not self.info:
                try:
                    self.info = Info(self.base_url, skip_ws=True)
                except:
                    return {}
                    
            all_mids = self.info.all_mids()
            return {k: float(v) for k, v in all_mids.items()}
        except Exception as e:
            logger.error(f"Failed to fetch all prices: {e}")
            return {}

    async def get_ohlcv(self, pair, timeframe, since=None, limit=100):
        # Use CCXT for standardized data fetching
        try:
            import ccxt.async_support as ccxt
            
            if not hasattr(self, 'ccxt_client'):
                self.ccxt_client = ccxt.hyperliquid({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'future'}
                })
            
            ohlcv = await self.ccxt_client.fetch_ohlcv(pair, timeframe, since, limit)
            return ohlcv
            
        except Exception as e:
            logger.error(f"CCXT Fetch Failed: {e}")
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
            # Lazy init info if needed
            if not self.info:
                try:
                    self.info = Info(self.base_url, skip_ws=True)
                except Exception as e:
                    logger.error(f"Failed to lazy-init Info for get_user_positions: {e}")
                    return []

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
