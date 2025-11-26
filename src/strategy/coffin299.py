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
        
        # Adjust for Binance Japan (No stablecoins)
        if config.get('active_exchange') == 'binance_japan':
            quote = config.get('exchanges', {}).get('binance_japan', {}).get('quote_currency', 'BTC')
            self.target_pair = f"ETH/{quote}"
            logger.info(f"Binance Japan Mode: Target Pair set to {self.target_pair}")
            
        self.last_gemini_poll = datetime.min
        self.last_hourly_report = datetime.utcnow()
        self.gemini_interval = timedelta(minutes=config['ai']['polling_interval_minutes'])
        self.timeframe = config['strategy']['timeframe']
        
        # State
        self.current_recommendation = None

    async def run_cycle(self):
        """
        Main strategy cycle.
        """
        now = datetime.utcnow()
        
        # 0. Hourly Report
        if now - self.last_hourly_report > timedelta(hours=1):
            await self.report_hourly_status()
            self.last_hourly_report = now
        
        # 1. Poll Gemini if needed
        if now - self.last_gemini_poll > self.gemini_interval:
            await self.poll_gemini()
            self.last_gemini_poll = now
            
        # 2. Execute Trading Logic on Target Pair
        await self.execute_trading_logic(self.target_pair)

    async def report_hourly_status(self):
        """
        Sends an hourly update of the wallet balance.
        """
        try:
            balance = await self.exchange.get_balance()
            # Calculate total value in JPY (Approximate)
            # This requires fetching rates for all assets, which might be heavy.
            # For now, we'll try to get the quote currency total and convert to JPY if possible.
            
            total_balance_jpy = 0
            changes = {}
            
            # Simple estimation: Get BTC/JPY or ETH/JPY rate
            jpy_rate = 1.0
            quote_currency = "BTC" # Default
            
            if self.config.get('active_exchange') == 'binance_japan':
                 quote_currency = self.config.get('exchanges', {}).get('binance_japan', {}).get('quote_currency', 'BTC')
            
            # Try to get JPY rate for the quote currency
            try:
                if quote_currency != "JPY":
                    jpy_pair = f"{quote_currency}/JPY"
                    jpy_rate = await self.exchange.get_market_price(jpy_pair)
            except Exception:
                logger.warning(f"Could not fetch {quote_currency}/JPY rate. Using 1.0")
            
            # Sum up balances (very simplified)
            # ideally we iterate over all non-zero balances
            if isinstance(balance, dict):
                 # This depends on the exchange response structure (ccxt vs others)
                 # CCXT 'total' key usually holds the total balances
                 # In paper mode, the balance dict itself is the assets
                 total_assets = balance.get('total', balance)
                 for asset, amount in total_assets.items():
                     if amount > 0:
                         # Convert to quote then JPY
                         asset_val_in_quote = 0
                         if asset == quote_currency:
                             asset_val_in_quote = amount
                         else:
                             try:
                                 price = await self.exchange.get_market_price(f"{asset}/{quote_currency}")
                                 asset_val_in_quote = amount * price
                             except:
                                 pass # Skip if no pair
                         
                         total_balance_jpy += asset_val_in_quote * jpy_rate
                         changes[asset] = f"{amount:.4f}"

            await self.notifier.notify_balance(total_balance_jpy, "JPY", changes)
            logger.info(f"Hourly Report Sent. Total Est: {total_balance_jpy} JPY")

        except Exception as e:
            logger.error(f"Failed to send hourly report: {e}")

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
            try:
                amount = 0.001 # Mock amount
                order = await self.exchange.create_order(pair, 'market', 'buy', amount, current_price)
                if order:
                    # Calculate JPY value
                    total_jpy = await self._calculate_jpy_value(pair, amount, current_price)
                    await self.notifier.notify_trade("BUY", pair, current_price, amount, reason, total_jpy=total_jpy)
            except Exception as e:
                logger.error(f"BUY Order Failed: {e}")
            
        elif action == "SELL":
            # Check if we have the asset
            # This needs proper balance checking logic
            try:
                amount = 0.001 # Mock amount
                # TODO: Check actual balance of the asset before selling
                
                order = await self.exchange.create_order(pair, 'market', 'sell', amount, current_price)
                if order:
                    # Calculate JPY value
                    total_jpy = await self._calculate_jpy_value(pair, amount, current_price)
                    await self.notifier.notify_trade("SELL", pair, current_price, amount, reason, total_jpy=total_jpy)
            except Exception as e:
                logger.error(f"SELL Order Failed: {e}")

    async def _calculate_jpy_value(self, pair, amount, price):
        """
        Calculates the JPY value of a trade.
        """
        try:
            # pair is like ETH/BTC
            base, quote = pair.split('/')
            
            # Value in quote currency
            val_in_quote = amount * price
            
            if quote == "JPY":
                return val_in_quote
            
            # Fetch Quote/JPY rate (e.g. BTC/JPY)
            jpy_pair = f"{quote}/JPY"
            jpy_rate = await self.exchange.get_market_price(jpy_pair)
            
            return val_in_quote * jpy_rate
        except Exception as e:
            logger.warning(f"Failed to calculate JPY value: {e}")
            return None

    def calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
