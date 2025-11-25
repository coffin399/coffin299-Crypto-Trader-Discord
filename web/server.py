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
from src.logger import setup_logger
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
    strategy = Coffin299Strategy(config, exchange, ai, discord_notifier)
    
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
    
    return {
        "status": "Running",
        "target_pair": strategy.target_pair,
        "recommendation": strategy.current_recommendation,
        "balance": balance,
        "paper_mode": exchange.paper_mode
    }

if __name__ == "__main__":
    url = f"http://{config['webui']['host']}:{config['webui']['port']}"
    if config['webui']['host'] == "0.0.0.0":
        url = f"http://localhost:{config['webui']['port']}"
        
    logger.info(f"Opening browser at {url}")
    webbrowser.open(url)
    
    uvicorn.run(app, host=config['webui']['host'], port=config['webui']['port'])
