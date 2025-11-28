import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from ..logger import setup_logger

logger = setup_logger("ai_learner")

class StrategyLearner:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False
        self.feature_cols = ['rsi', 'sma_diff', 'volatility', 'volume_change']

    def prepare_data(self, df):
        """
        Prepares features and labels from OHLCV DataFrame.
        """
        data = df.copy()
        
        # Ensure numeric
        cols = ['open', 'high', 'low', 'close', 'volume']
        for col in cols:
            data[col] = data[col].astype(float)

        # Feature Engineering
        # 1. RSI
        data['rsi'] = self.calculate_rsi(data['close'])
        
        # 2. SMA Diff (Fast - Slow)
        data['sma_fast'] = data['close'].rolling(window=12).mean()
        data['sma_slow'] = data['close'].rolling(window=26).mean()
        data['sma_diff'] = (data['sma_fast'] - data['sma_slow']) / data['close']
        
        # 3. Volatility (ATR-like or StdDev)
        data['volatility'] = data['close'].rolling(window=20).std() / data['close']
        
        # 4. Volume Change
        data['volume_change'] = data['volume'].pct_change()
        
        # Target: 1 if next close > current close, else 0
        data['target'] = (data['close'].shift(-1) > data['close']).astype(int)
        
        # Drop NaNs created by rolling/shifting
        data.dropna(inplace=True)
        
        return data

    def calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def train(self, ohlcv_data):
        """
        Trains the model using provided OHLCV data.
        ohlcv_data: List of lists or DataFrame
        """
        logger.info("Starting model training...")
        
        if isinstance(ohlcv_data, list):
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        else:
            df = ohlcv_data.copy()
            
        if len(df) < 200:
            logger.warning("Not enough data to train model (need > 200 rows).")
            return False

        data = self.prepare_data(df)
        
        X = data[self.feature_cols]
        y = data['target']
        
        # Split (Time-series split is better, but random split ok for simple demo)
        # Actually, for time series, we should train on past, test on recent.
        # But here we just want to train on all available history to be ready for *future* (live).
        # So we train on everything.
        
        try:
            self.model.fit(X, y)
            self.is_trained = True
            logger.info(f"Model trained successfully on {len(X)} samples.")
            return True
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False

    def predict(self, current_df):
        """
        Predicts 'BUY', 'SELL', or 'HOLD' based on current data.
        current_df: DataFrame containing recent candles (enough to calculate features)
        """
        if not self.is_trained:
            return "HOLD", 0.0

        try:
            data = self.prepare_data(current_df)
            if data.empty:
                return "HOLD", 0.0
                
            # Take the last row
            last_row = data.iloc[[-1]][self.feature_cols]
            
            prediction = self.model.predict(last_row)[0]
            probability = self.model.predict_proba(last_row)[0][1] # Prob of class 1 (Up)
            
            # Thresholds
            if prediction == 1 and probability > 0.6:
                return "BUY", probability
            elif prediction == 0 and probability < 0.4: # Prob of Up is low -> Down
                return "SELL", 1 - probability
            else:
                return "HOLD", probability
                
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return "HOLD", 0.0
