import ta
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class Coffin299Strategy:
    def __init__(self, ema_fast=12, ema_slow=26, stoch_k=3, stoch_d=3, stoch_rsi=14, stoch_window=14, overbought=80, oversold=20, **kwargs):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.stoch_k = stoch_k
        self.stoch_d = stoch_d
        self.stoch_rsi = stoch_rsi
        self.stoch_window = stoch_window
        self.overbought = overbought
        self.oversold = oversold

    def analyze(self, df):
        """
        Analyzes the dataframe and returns a signal: 'BUY', 'SELL', or None.
        Freqtrade-style Scalping: StochRSI + EMA Crossover
        """
        if df.empty:
            return None

        # 1. Calculate EMAs (Trend)
        df['ema_fast'] = ta.trend.EMAIndicator(close=df['close'], window=self.ema_fast).ema_indicator()
        df['ema_slow'] = ta.trend.EMAIndicator(close=df['close'], window=self.ema_slow).ema_indicator()

        # 2. Calculate Stochastic RSI (Momentum)
        stoch_rsi = ta.momentum.StochRSIIndicator(
            close=df['close'], 
            window=self.stoch_rsi, 
            smooth1=self.stoch_k, 
            smooth2=self.stoch_d
        )
        df['fastk'] = stoch_rsi.stochrsi_k() * 100
        df['fastd'] = stoch_rsi.stochrsi_d() * 100

        current_price = df['close'].iloc[-1]
        ema_fast_val = df['ema_fast'].iloc[-1]
        ema_slow_val = df['ema_slow'].iloc[-1]
        fastk = df['fastk'].iloc[-1]
        fastd = df['fastd'].iloc[-1]
        
        logger.info(f"Price: {current_price:.6f} | EMA12: {ema_fast_val:.6f} | EMA26: {ema_slow_val:.6f} | StochK: {fastk:.2f} | StochD: {fastd:.2f}")

        # Logic
        # Pure StochRSI Scalping (Mean Reversion)
        # BUY: StochK < Oversold
        if fastk < self.oversold:
            return 'BUY'
        
        # SELL: StochK > Overbought
        elif fastk > self.overbought:
            return 'SELL'
            
        return None
