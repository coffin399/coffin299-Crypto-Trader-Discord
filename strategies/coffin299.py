import ta
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class HyperTrendStrategy:
    def __init__(self, ema_fast=12, ema_slow=26, macd_signal=9, atr_period=14, atr_multiplier_sl=2.0, atr_multiplier_tp=3.0, rsi_period=14, rsi_overbought=70, rsi_oversold=30, **kwargs):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.macd_signal = macd_signal
        self.atr_period = atr_period
        self.atr_multiplier_sl = atr_multiplier_sl
        self.atr_multiplier_tp = atr_multiplier_tp
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

    def analyze(self, df):
        """
        Analyzes the dataframe and returns a signal dict or None.
        Strategy: HyperTrend (EMA Cross + MACD + RSI + ATR)
        """
        if df.empty:
            return None

        # 1. Calculate Indicators
        # EMA
        df['ema_fast'] = ta.trend.EMAIndicator(close=df['close'], window=self.ema_fast).ema_indicator()
        df['ema_slow'] = ta.trend.EMAIndicator(close=df['close'], window=self.ema_slow).ema_indicator()
        
        # MACD
        macd = ta.trend.MACD(close=df['close'], window_slow=self.ema_slow, window_fast=self.ema_fast, window_sign=self.macd_signal)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=self.rsi_period).rsi()
        
        # ATR
        df['atr'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=self.atr_period).average_true_range()

        # Current Values
        current_price = df['close'].iloc[-1]
        ema_fast_val = df['ema_fast'].iloc[-1]
        ema_slow_val = df['ema_slow'].iloc[-1]
        macd_val = df['macd'].iloc[-1]
        macd_signal_val = df['macd_signal'].iloc[-1]
        rsi_val = df['rsi'].iloc[-1]
        atr_val = df['atr'].iloc[-1]
        
        logger.info(f"Price: {current_price:.2f} | EMA12: {ema_fast_val:.2f} | EMA26: {ema_slow_val:.2f} | MACD: {macd_val:.2f} | RSI: {rsi_val:.2f}")

        # Logic
        signal = None
        
        # BUY Signal
        # 1. Fast EMA > Slow EMA (Trend Up)
        # 2. MACD > Signal (Momentum Up)
        # 3. RSI < Overbought (Not extended)
        if (ema_fast_val > ema_slow_val) and (macd_val > macd_signal_val) and (rsi_val < self.rsi_overbought):
            signal = 'BUY'
            
        # SELL Signal
        # 1. Fast EMA < Slow EMA (Trend Down)
        # 2. MACD < Signal (Momentum Down)
        # 3. RSI > Oversold (Not extended)
        elif (ema_fast_val < ema_slow_val) and (macd_val < macd_signal_val) and (rsi_val > self.rsi_oversold):
            signal = 'SELL'
            
        if signal:
            return {
                'signal': signal,
                'sl': current_price - (atr_val * self.atr_multiplier_sl) if signal == 'BUY' else current_price + (atr_val * self.atr_multiplier_sl),
                'tp': current_price + (atr_val * self.atr_multiplier_tp) if signal == 'BUY' else current_price - (atr_val * self.atr_multiplier_tp)
            }
            
        return None
