import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_loader import load_config
from src.logger import setup_logger
from src.exchanges.trade_xyz import TradeXYZ
from src.exchanges.hyperliquid import Hyperliquid
from src.exchanges.binance_japan import BinanceJapan
from src.exchanges.tread_fi import TreadFi
from src.ai.gemini_service import GeminiService
from src.notifications.discord_bot import DiscordNotifier

logger = setup_logger("main")

async def main_loop(strategy):
    logger.info("Starting Main Strategy Loop...")
    while True:
        try:
            await strategy.run_cycle()
        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")
        
        # Sleep for 60 seconds (loop interval)
        await asyncio.sleep(60) 

async def start_bot():
    config = load_config()
    
    # Init Exchange
    exchange_name = config.get('active_exchange', 'trade_xyz')
    logger.info(f"Initializing Exchange: {exchange_name}")
    
    if exchange_name == 'hyperliquid':
        exchange = Hyperliquid(config)
    elif exchange_name == 'binance_japan':
        exchange = BinanceJapan(config)
    elif exchange_name == 'tread_fi':
        exchange = TreadFi(config)
    else:
        exchange = TradeXYZ(config)
        
    # Init AI
    api_keys = config['ai'].get('api_keys') or config['ai'].get('api_key')
    
    ai = GeminiService(
        api_keys=api_keys,
        model_name=config['ai']['model'],
        system_prompt=config['ai']['system_prompt']
    )
    
    # Init Discord
    discord_notifier = DiscordNotifier(config)
    
    # Start Discord Client
    await discord_notifier.start()
    
    # Start Exchange WebSocket if supported
    if exchange_name == 'tread_fi':
        asyncio.create_task(exchange.start_websocket())
    elif exchange_name == 'hyperliquid':
        asyncio.create_task(exchange.start_websocket())
    
    # Init Strategy
    strategy_type = config['strategy'].get('type', 'coffin299')
    logger.info(f"Initializing Strategy: {strategy_type}")
    
    if strategy_type == 'copy_leaderboard':
        from src.strategy.coffin299_copy import Coffin299CopyStrategy
        strategy = Coffin299CopyStrategy(config, exchange, ai, discord_notifier)
        logger.info("Started in Copy Trading Mode")
    else:
        from src.strategy.coffin299 import Coffin299Strategy
        strategy = Coffin299Strategy(config, exchange, ai, discord_notifier)
        logger.info("Started in Standard AI Mode")
    
    try:
        await main_loop(strategy)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        pass
