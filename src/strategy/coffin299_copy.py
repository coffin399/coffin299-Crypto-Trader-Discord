import asyncio
import aiohttp
from datetime import datetime, timedelta
from ..logger import setup_logger

logger = setup_logger("strategy_copy")

class Coffin299CopyStrategy:
    def __init__(self, config, exchange, ai, notifier):
        self.config = config
        self.exchange = exchange
        self.ai = ai
        self.notifier = notifier
        
        self.target_pair = "COPY_TRADING" # Virtual pair name
        self.current_recommendation = {"action": "COPY", "confidence": 1.0}
        
        self.top_traders = []
        self.last_leaderboard_update = datetime.min
        self.jpy_rate = 150.0 # Default fallback

        # Start background tasks
        asyncio.create_task(self.update_jpy_rate_loop())
        asyncio.create_task(self.periodic_report_loop())

    async def run_cycle(self):
        """
        Main copy strategy cycle.
        """
        # 1. Update Leaderboard (every 1 hour)
        if datetime.utcnow() - self.last_leaderboard_update > timedelta(hours=1):
            await self.update_leaderboard()
            
        if not self.top_traders:
            logger.warning("No top traders found to copy.")
            return

        # 2. Analyze Top Traders' Positions
        # logger.info(f"Analyzing positions of {len(self.top_traders)} top traders: {self.top_traders}")
        
        aggregate_positions = {} # { 'ETH': {'LONG': 0, 'SHORT': 0} }
        
        for address in self.top_traders:
            positions = await self.exchange.get_user_positions(address)
            for pos in positions:
                symbol = pos['symbol']
                side = pos['side']
                
                if symbol not in aggregate_positions:
                    aggregate_positions[symbol] = {'LONG': 0, 'SHORT': 0}
                
                aggregate_positions[symbol][side] += 1
                
        my_pos = next((p for p in current_positions if p['symbol'] == symbol), None)

        # Logic for SELL (Shorting vs Closing)
        if side == "SELL":
            # If we have a LONG position, this SELL is a CLOSE/REDUCE -> Always Allowed
            if my_pos and my_pos['side'] == 'LONG' and my_pos['size'] > 0:
                pass # Allowed (Closing Long)
            
            # If we have NO position or a SHORT position, this SELL is a NEW SHORT or ADDING SHORT
            else:
                if not allow_short:
                    logger.info(f"Skipping SELL (Short) for {pair} because allow_short is False.")
                    return

        if max_positions > 0:
            # If we don't have a position, this is a new OPEN trade
            if not my_pos:
                if len(current_positions) >= max_positions:
                    logger.warning(f"Max Open Positions Reached ({len(current_positions)}/{max_positions}). Skipping OPEN trade for {pair}.")
                    return

        price = await self.exchange.get_market_price(pair)
        
        logger.info(f"EXECUTING COPY TRADE: {side} {pair} @ {price} ({reason})")
        
        order_side = side.lower()
        
        # Calculate Amount based on max_quantity (JPY)
        max_quantity_jpy = self.config['strategy'].get('copy_trading', {}).get('max_quantity', 1500) # Default 1500 JPY (~$10)
        
        # 1. Convert JPY to USD
        usd_value = max_quantity_jpy / self.jpy_rate
        
        # 2. Convert USD to Token Amount
        # Amount = USD / Price
        amount = usd_value / price
        
        # Rounding (Hyperliquid usually takes 4-5 decimals, let's safe round to 4 significant digits or fixed decimals)
        # For safety/simplicity, let's use 6 decimals for now to support small amounts (e.g. 500 JPY on BTC)
        # Ideally we should check lot size rules from exchange info.
        amount = round(amount, 6)
        
        if amount <= 0:
            logger.warning(f"Calculated amount is too small: {amount} (JPY: {max_quantity_jpy}, Price: {price})")
            return
        
        try:
            order = await self.exchange.create_order(pair, 'market', order_side, amount)
            if order:
                logger.info(f"Trade Executed: {order}")
                
                # Calculate JPY Value (Actual)
                total_jpy = amount * price * self.jpy_rate
                
                await self.notifier.notify_trade(side, pair, price, str(amount), reason, total_jpy=total_jpy)
            else:
                logger.error("Trade Execution Failed")
        except Exception as e:
            logger.error(f"Trade Execution Error: {e}")

    async def update_jpy_rate_loop(self):
        logger.info("Starting JPY Rate Polling Task...")
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            rate = data.get('rates', {}).get('JPY')
                            if rate:
                                self.jpy_rate = float(rate)
                                logger.info(f"Updated USD/JPY Rate: {self.jpy_rate}")
                            else:
                                logger.warning("JPY rate not found in API response")
                        else:
                            logger.warning(f"Failed to fetch exchange rate: {resp.status}")
            except Exception as e:
                logger.error(f"Error fetching exchange rate: {e}")
                
            await asyncio.sleep(3600) # 1 hour

    async def periodic_report_loop(self):
        logger.info("Starting Periodic Report Task (Every 30 mins)...")
        
        # Initial Report
        await asyncio.sleep(5) # Wait a bit for startup
        await self.send_report()
        
        while True:
            # Wait 30 minutes
            await asyncio.sleep(1800)
            await self.send_report()

    async def send_report(self):
        try:
            balance = await self.exchange.get_balance()
            total_usd = float(balance.get('total', {}).get('USDC', 0))
            total_jpy = total_usd * self.jpy_rate
            
            positions = await self.exchange.get_positions()
            pos_summary = {}
            for p in positions:
                pos_summary[p['symbol']] = f"{p['size']} ({p['pnl']:.2f} USD)"
            
            await self.notifier.notify_balance(total_jpy, currency="JPY", changes=pos_summary)
            logger.info(f"Sent Periodic Report. Total: ${total_usd:.2f} (¥{total_jpy:.0f})")
        except Exception as e:
            logger.error(f"Error in periodic report: {e}")
