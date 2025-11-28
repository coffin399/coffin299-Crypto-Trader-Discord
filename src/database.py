import sqlite3
import os
from .logger import setup_logger

logger = setup_logger("database")

class PositionDB:
    def __init__(self, db_path="coffin299.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create paper_positions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS paper_positions (
                    symbol TEXT PRIMARY KEY,
                    amount REAL,
                    entry_price REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to init DB: {e}")

    def save_position(self, symbol, amount, entry_price):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if amount == 0:
                cursor.execute("DELETE FROM paper_positions WHERE symbol = ?", (symbol,))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO paper_positions (symbol, amount, entry_price, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (symbol, amount, entry_price))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save position {symbol}: {e}")

    def load_positions(self):
        positions = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT symbol, amount, entry_price FROM paper_positions")
            rows = cursor.fetchall()
            
            for row in rows:
                # row: (symbol, amount, entry_price)
                # BaseExchange format: {pair: {amount: ..., entry_price: ...}}
                # Note: DB stores 'ETH', but BaseExchange uses 'ETH/USDC'.
                # We assume standard pair format here or store full pair in DB.
                # Let's assume we stored the full pair name as 'symbol' in DB.
                positions[row[0]] = {'amount': row[1], 'entry_price': row[2]}
                
            conn.close()
        except Exception as e:
            logger.error(f"Failed to load positions: {e}")
            
        return positions
