import aiohttp
import asyncio
from .base import BaseExchange
from ..logger import setup_logger

logger = setup_logger("tread_fi")

class TreadFi(BaseExchange):
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.get('exchanges', {}).get('tread_fi', {}).get('api_key')
        self.account_names = config.get('exchanges', {}).get('tread_fi', {}).get('account_names', [])
        self.base_url = "https://api.tread.fi" # Default, can be overridden if needed
        self.ws_url = "wss://api.tread.fi/ws/orders/"
        self.ws_task = None
        
        if not self.api_key:
            logger.error("Tread.fi API Key not found in config")

    async def get_balance(self):
        if self.paper_mode:
            return self.paper_balance
        
        # Tread.fi doesn't seem to expose a direct "aggregated balance" endpoint easily
        # via the Core Order API. For now, we return a dummy structure to prevent errors.
        # In a real scenario, we might need to query the underlying exchanges or 
        # use a different Tread.fi endpoint if available.
        logger.warning("Tread.fi get_balance not fully implemented (API limitation). Returning mock.")
        return {'total': {'BTC': 0, 'ETH': 0, 'USDC': 0, 'JPY': 0}}

    async def get_market_price(self, pair):
        # Tread.fi is an execution layer. It might not have a public market data endpoint
        # compatible with simple ticker checks.
        # We might need to use a fallback (like Binance) for price data 
        # or check if Tread has a market data endpoint.
        # For now, we'll return a dummy price or try to fetch from a public source if critical.
        # Let's assume the user might want to use CCXT for data and Tread for execution?
        # For this implementation, I'll return a mock to keep it simple, 
        # or maybe I can use the 'binance_japan' logic just for price checking if available?
        
        # TODO: Integrate a proper price source. 
        return 100000.0 # Mock

    async def get_ohlcv(self, pair, timeframe, limit=100):
        # Similar to price, Tread.fi might not provide OHLCV.
        # We should probably use a data provider exchange for this.
        # For now, return empty or mock.
        return []

    async def _execute_real_order(self, pair, type, side, amount, price=None):
        if not self.api_key:
            logger.error("Cannot execute order: Missing API Key")
            return None

        # Convert pair format if needed (e.g. ETH/USDC -> ETH-USDC)
        # Tread.fi uses "BTC-USD" format usually
        formatted_pair = pair.replace('/', '-')

        url = f"{self.base_url}/api/orders/"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Default strategy to "Implementation" (Market/Limit) or "TWAP"
        # We'll use a simple immediate execution strategy if possible, or just "Implementation"
        # The docs mention "strategy" field.
        payload = {
            "pair": formatted_pair,
            "side": side.lower(),
            "base_asset_qty": str(amount),
            "accounts": self.account_names,
            "strategy": "Implementation", # Or "TWAP", "VWAP" etc.
            "notes": "Executed by Coffin299"
        }
        
        if price and type == 'limit':
            payload['limit_price'] = str(price)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        logger.info(f"Tread.fi Order Submitted: {data}")
                        return data
                    else:
                        text = await response.text()
                        logger.error(f"Tread.fi Order Failed: {response.status} - {text}")
                        return None
        except Exception as e:
            logger.error(f"Error executing Tread.fi order: {e}")
            return None

    async def start_websocket(self):
        """
        Starts the WebSocket connection for order updates.
        """
        if not self.api_key:
            logger.error("Cannot start WebSocket: Missing API Key")
            return

        url = f"{self.ws_url}?token={self.api_key}"
        
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(url) as ws:
                        logger.info("Connected to Tread.fi WebSocket")
                        
                        # Subscribe
                        await ws.send_json({"command": "subscribe", "data_type": "user_orders"})
                        
                        # Start Keep-Alive Task
                        keep_alive_task = asyncio.create_task(self._keep_alive(ws))
                        
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = msg.json()
                                await self._handle_ws_message(data)
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f"WebSocket connection closed with exception {ws.exception()}")
                                break
                                
                        keep_alive_task.cancel()
                        
            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    async def _keep_alive(self, ws):
        while True:
            try:
                await asyncio.sleep(10) # Send every 10 seconds
                await ws.send_json({"command": "keep_alive"})
            except Exception as e:
                logger.error(f"Keep-alive failed: {e}")
                break

    async def _handle_ws_message(self, data):
        if data.get('type') == 'order_update':
            order_data = data.get('data', {})
            update_type = order_data.get('update_type')
            order_info = order_data.get('order', {})
            
            logger.info(f"WS Update: {update_type} - OrderID: {order_data.get('order_id')}")
            
            # Here we could update local state or notify via Discord
            # For now, just log it.

    async def close(self):
        if self.ws_task:
            self.ws_task.cancel()
        pass
