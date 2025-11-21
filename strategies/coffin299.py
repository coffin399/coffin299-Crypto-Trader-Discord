import pandas_ta as ta
import pandas as pd

class Coffin299Strategy:
    def __init__(self, rsi_period=14, rsi_overbought=70, rsi_oversold=30, bb_period=20, bb_std=2.0):
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.bb_period = bb_period
        self.bb_std = bb_std

    def analyze(self, df):
        """
        Analyzes the dataframe and returns a signal: 'BUY', 'SELL', or None.
        """
        if df.empty:
            return None

        # Calculate Indicators
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)
        bb = ta.bbands(df['close'], length=self.bb_period, std=self.bb_std)
        
        # Rename columns for easier access (pandas_ta names can be verbose)
        # Example: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        df['bb_lower'] = bb[f'BBL_{self.bb_period}_{self.bb_std}']
        df['bb_upper'] = bb[f'BBU_{self.bb_period}_{self.bb_std}']

        current_price = df['close'].iloc[-1]
        current_rsi = df['rsi'].iloc[-1]
        current_bb_lower = df['bb_lower'].iloc[-1]
        current_bb_upper = df['bb_upper'].iloc[-1]

        # Logic
        # Buy Signal: Price <= Lower BB AND RSI <= Oversold
        if current_price <= current_bb_lower and current_rsi <= self.rsi_oversold:
            return 'BUY'
        
        # Sell Signal: Price >= Upper BB AND RSI >= Overbought
        elif current_price >= current_bb_upper and current_rsi >= self.rsi_overbought:
            return 'SELL'
        
        return None
