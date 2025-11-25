import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_loader import load_config
from src.logger import setup_logger
from src.exchanges.trade_xyz import TradeXYZ
from src.exchanges.hyperliquid import Hyperliquid
from src.ai.gemini_service import GeminiService
from src.notifications.discord_bot import DiscordNotifier
from src.strategy.coffin299 import Coffin299Strategy

logger = setup_logger("main")

async def main_loop(strategy):
    logger.info("Starting Main Strategy Loop...")
    while True:
        try:
            await strategy.run_cycle()
        except Exception as e:
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_loader import load_config
from src.logger import setup_logger
from src.exchanges.trade_xyz import TradeXYZ
from src.exchanges.hyperliquid import Hyperliquid
from src.ai.gemini_service import GeminiService
from src.notifications.discord_bot import DiscordNotifier
from src.strategy.coffin299 import Coffin299Strategy

logger = setup_logger("main")

async def main_loop(strategy):
    logger.info("Starting Main Strategy Loop...")
    while True:
        try:
            await strategy.run_cycle()
        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")
        
        # Sleep for 15 minutes (or less for testing)
        # For demo purposes, we sleep 60 seconds
        await asyncio.sleep(60) 

async def start_bot():
    config = load_config()
    
    # Init Exchange
    exchange_name = config.get('active_exchange', 'trade_xyz')
    if exchange_name == 'hyperliquid':
        exchange = Hyperliquid(config)
    else:
        exchange = TradeXYZ(config)
        
    # Init AI
    ai = GeminiService(
        api_key=config['ai']['api_key'],
        model_name=config['ai']['model'],
        system_prompt=config['ai']['system_prompt']
    )
    
    # Init Discord
    discord_notifier = DiscordNotifier(config)
    
    # Start Discord Client
    await discord_notifier.start()
    
    # Init Strategy
    strategy = Coffin299Strategy(config, exchange, ai, discord_notifier)
    
    # Start WebUI (TODO: Integrate FastAPI here)
    # For now, we just run the loop
    
    try:
        await main_loop(strategy)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")

if __name__ == "__main__":
    asyncio.run(start_bot())
