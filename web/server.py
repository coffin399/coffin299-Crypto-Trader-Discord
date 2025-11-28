from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import sys
import os
from contextlib import asynccontextmanager
import webbrowser

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_loader import load_config
from src.logger import setup_logger, log_buffer
from src.exchanges.trade_xyz import TradeXYZ
from src.exchanges.hyperliquid import Hyperliquid
from src.exchanges.binance_japan import BinanceJapan
from src.ai.gemini_service import GeminiService
from src.notifications.discord_bot import DiscordNotifier
from src.strategy.coffin299 import Coffin299Strategy

logger = setup_logger("web_server")
config = load_config()

# Global Bot State
bot_state = {
    "strategy": None,
    "exchange": None
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Bot Components...")
    
    # Init Exchange
    exchange_name = config.get('active_exchange', 'trade_xyz')
    if exchange_name == 'hyperliquid':
        exchange = Hyperliquid(config)
    elif exchange_name == 'binance_japan':
        exchange = BinanceJapan(config)
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
    await discord_notifier.start()
    
    # Init Strategy
    strategy_type = config['strategy'].get('type', 'coffin299')
    if strategy_type == 'copy_leaderboard':
        from src.strategy.coffin299_copy import Coffin299CopyStrategy
        strategy = Coffin299CopyStrategy(config, exchange, ai, discord_notifier)
        logger.info("Started in Copy Trading Mode")
    else:
        from src.strategy.coffin299 import Coffin299Strategy
        strategy = Coffin299Strategy(config, exchange, ai, discord_notifier)
        logger.info("Started in Standard AI Mode")
    
    bot_state["strategy"] = strategy
    bot_state["exchange"] = exchange
    
    # Start Strategy Loop Task
    task = asyncio.create_task(run_strategy_loop(strategy))
    
    yield
    
    # Cleanup if needed
    task.cancel()
    await exchange.close()

app = FastAPI(lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

async def run_strategy_loop(strategy):
    logger.info("Starting Strategy Loop Background Task...")
    while True:
        try:
            await strategy.run_cycle()
        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")
        await asyncio.sleep(60) # 1 min loop for demo

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Coffin299 Trader"})

@app.get("/api/status")
async def get_status():
    strategy = bot_state["strategy"]
    exchange = bot_state["exchange"]
    
    if not strategy or not exchange:
        return {"status": "Initializing"}
        
    balance = await exchange.get_balance()
    
    # Calculate JPY Total (Simplified)
    total_jpy = 0
    # Reuse strategy logic if possible, or simple estimation here
    # For now, we'll try to use the strategy's helper if available, or just send raw balance
    # and let frontend handle it? No, backend is better.
    
    # Quick dirty JPY calc (assuming 1 USDC = 150 JPY for demo if price fetch fails)
    # Ideally we use strategy._calculate_jpy_value but that's for trade amount.
    # Let's try to get a rough estimate.
    try:
        # Assuming balance has 'total' key
        assets = balance.get('total', balance)
        usdc_val = 0
        
        # Get prices
        eth_price = await exchange.get_market_price("ETH/USDC") or 3000
        btc_price = await exchange.get_market_price("BTC/USDC") or 90000
        usdc_jpy = 150 # Mock/Default
        
        # Try to fetch USDC/JPY if possible (unlikely on crypto exchange)
        # So we use a fixed rate or fetch from external? 
        # For this demo, fixed 150 is fine or we can add it to config.
        
        for coin, amount in assets.items():
            if amount <= 0: continue
            if coin == 'USDC':
                usdc_val += amount
            elif coin == 'ETH':
                usdc_val += amount * eth_price
            elif coin == 'BTC':
                usdc_val += amount * btc_price
                
        total_jpy = usdc_val * usdc_jpy
        
    except Exception as e:
        logger.error(f"Error calculating JPY: {e}")

    # Fetch Positions
    positions = []
    if hasattr(exchange, 'get_positions'):
        positions = await exchange.get_positions()

    return {
        "status": "Running",
        "target_pair": strategy.target_pair,
        "recommendation": strategy.current_recommendation,
        "balance": balance,
        "total_jpy": total_jpy,
        "paper_mode": exchange.paper_mode,
        "positions": positions,
        "logs": list(log_buffer)
    }

if __name__ == "__main__":
    url = f"http://{config['webui']['host']}:{config['webui']['port']}"
    if config['webui']['host'] == "0.0.0.0":
        url = f"http://localhost:{config['webui']['port']}"
        
    logger.info(f"Opening browser at {url}")
    webbrowser.open(url)
    
    uvicorn.run(app, host=config['webui']['host'], port=config['webui']['port'], log_level="warning")
