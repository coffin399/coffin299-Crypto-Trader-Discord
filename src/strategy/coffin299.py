import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ..logger import setup_logger

logger = setup_logger("strategy_coffin299")

class Coffin299Strategy:
    def __init__(self, config, exchange, ai_service, notifier):
        self.config = config
        self.exchange = exchange
        self.ai = ai_service
        self.notifier = notifier
        
        self.target_pair = "ETH/USDC" # Default
        self.last_gemini_poll = datetime.min
        self.gemini_interval = timedelta(minutes=config['ai']['polling_interval_minutes'])
        self.timeframe = config['strategy']['timeframe']
        
        # State
        self.current_recommendation = None

    async def run_cycle(self):
        """
        Main strategy cycle.
        """
        now = datetime.utcnow()
        
        # 1. Poll Gemini if needed
        if now - self.last_gemini_poll > self.gemini_interval:
            await self.poll_gemini()
            self.last_gemini_poll = now
            
        # 2. Execute Trading Logic on Target Pair
        await self.execute_trading_logic(self.target_pair)

    async def poll_gemini(self):
        logger.info("Polling Gemini for strategic direction...")
        
        # Get market summary (simplified for now, ideally fetch top gainers/losers)
        # For this demo, we'll just feed it the current target pair's recent data
        ohlcv = await self.exchange.get_ohlcv(self.target_pair, "1h", limit=24)
        if not ohlcv:
            logger.warning("No data for Gemini.")
            return

        summary = f"Recent 24h data for {self.target_pair}: {ohlcv[-1]}" # Simplify
        
        decision = await self.ai.analyze_market(summary)
        self.current_recommendation = decision
        
        if decision.get('pair') and decision['pair'] != self.target_pair:
            logger.info(f"Gemini suggests switching to {decision['pair']}")
            # Logic to switch pairs (sell old, buy new) could go here
            # For now, we just update the target if we are in base currency
            # or if we want to force switch.
            # self.target_pair = decision['pair'] 
            pass

    async def execute_trading_logic(self, pair):
        ohlcv = await self.exchange.get_ohlcv(pair, self.timeframe, limit=50)
        if not ohlcv:
            return

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Indicators
        df['close'] = df['close'].astype(float)
        df['rsi'] = self.calculate_rsi(df['close'])
        
        current_rsi = df['rsi'].iloc[-1]
        current_price = df['close'].iloc[-1]
        
        logger.info(f"Analyzing {pair}: Price={current_price}, RSI={current_rsi}")
        
        # "Bang Bang" Logic (Aggressive)
        # Buy if RSI < 30 (Oversold) OR Gemini says BUY
        # Sell if RSI > 70 (Overbought) OR Gemini says SELL
        
        action = "HOLD"
        reason = ""
        
        gemini_action = self.current_recommendation.get('action') if self.current_recommendation else "HOLD"
        
        if current_rsi < 30 or gemini_action == "BUY":
            action = "BUY"
            reason = f"RSI {current_rsi:.2f} < 30 or Gemini BUY"
        elif current_rsi > 70 or gemini_action == "SELL":
            action = "SELL"
            reason = f"RSI {current_rsi:.2f} > 70 or Gemini SELL"
            
        if action == "BUY":
            # Check max open positions
            max_positions = self.config['strategy'].get('max_open_positions', 3)
            current_positions = len(self.exchange.positions)
            
            if max_positions > 0 and current_positions >= max_positions:
                logger.info(f"Skipping BUY: Max positions reached ({current_positions}/{max_positions})")
                return

            # Check balance (Base currency, e.g. USDC)
            # For demo, assume we buy 10% of available quote
            # This needs proper balance checking logic
            await self.exchange.create_order(pair, 'market', 'buy', 0.001, current_price) # Mock amount
            await self.notifier.notify_trade("BUY", pair, current_price, 0.001, reason)
            
        elif action == "SELL":
            # Check if we have the asset
            # This needs proper balance checking logic
            await self.exchange.create_order(pair, 'market', 'sell', 0.001, current_price) # Mock amount
            await self.notifier.notify_trade("SELL", pair, current_price, 0.001, reason)

    def calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
