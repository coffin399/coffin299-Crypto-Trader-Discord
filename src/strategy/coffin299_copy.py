import asyncio
from datetime import datetime, timedelta
from ..logger import setup_logger

logger = setup_logger("strategy_copy")

class Coffin299CopyStrategy:
    def __init__(self, config, exchange, ai_service, notifier):
        self.config = config
        self.exchange = exchange
        self.ai = ai_service
        self.notifier = notifier
        
        self.target_pair = "COPY_TRADING" # Virtual pair name
        self.current_recommendation = {"action": "COPY", "confidence": 1.0}
        
        # Cache
        self.top_traders = []
        self.last_leaderboard_update = datetime.min
        
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
        logger.info(f"Analyzing positions of {len(self.top_traders)} top traders...")
        
        aggregate_positions = {} # { 'ETH': {'LONG': 0, 'SHORT': 0} }
        
        for address in self.top_traders:
            positions = await self.exchange.get_user_positions(address)
            for pos in positions:
                symbol = pos['symbol']
                side = pos['side']
                
                if symbol not in aggregate_positions:
                    aggregate_positions[symbol] = {'LONG': 0, 'SHORT': 0}
                
                aggregate_positions[symbol][side] += 1
                
            await asyncio.sleep(0.5) # Rate limit friendly
            
        # 3. Decide & Execute
        # Logic: If > 50% of top traders are LONG on a coin, we LONG.
        
        target_coins = self.config['strategy'].get('copy_trading', {}).get('target_coins', [])
        
        for symbol, counts in aggregate_positions.items():
            # Filter by target coins if specified
            if target_coins and symbol not in target_coins:
                continue
                
            longs = counts['LONG']
            shorts = counts['SHORT']
            total = longs + shorts
            
            if total >= 2: # At least 2 traders in this coin
                logger.info(f"Copy Signal for {symbol}: {longs} LONG vs {shorts} SHORT")
                
                # Simple Majority Vote
                if longs > shorts:
                    # BUY
                    await self.execute_copy_trade(symbol, "BUY", f"Copying {longs}/{total} top traders")
                elif shorts > longs:
                    # SELL
                    await self.execute_copy_trade(symbol, "SELL", f"Copying {shorts}/{total} top traders")

    async def update_leaderboard(self):
        logger.info("Updating Leaderboard...")
        
        # Try API
        if hasattr(self.exchange, 'get_leaderboard_top_traders'):
            self.top_traders = await self.exchange.get_leaderboard_top_traders(limit=self.config['strategy'].get('copy_trading', {}).get('leaderboard_limit', 5))
            
        # Fallback if empty
        if not self.top_traders:
            logger.warning("API Leaderboard fetch failed or empty. Using fallback addresses from config.")
            fallback = self.config['strategy'].get('copy_trading', {}).get('fallback_addresses', [])
            # Filter out placeholders
            self.top_traders = [addr for addr in fallback if addr and "0x..." not in addr]
            
        logger.info(f"Top Traders to Copy: {self.top_traders}")
        self.last_leaderboard_update = datetime.utcnow()

    async def execute_copy_trade(self, symbol, side, reason):
        # Check if we already have this position
        # This requires position management logic similar to main strategy
        # For now, just notify/log
        
        pair = f"{symbol}/USDC"
        price = await self.exchange.get_market_price(pair)
        
        # Mock execution for now (or call real execute if safe)
        # To be safe, we just log/notify in this first version
        logger.info(f"EXECUTING COPY TRADE: {side} {pair} @ {price} ({reason})")
        
        # Notify
        await self.notifier.notify_trade(side, pair, price, "0.001", reason + " (Simulation)")
        
        # Real execution would go here:
        # await self.exchange.create_order(...)
