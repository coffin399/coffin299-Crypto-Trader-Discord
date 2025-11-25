from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
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

logger = setup_logger("web_server")
config = load_config()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Global Bot State
bot_state = {
    "strategy": None,
    "exchange": None
}

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing Bot Components...")
    
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
    discord = DiscordNotifier(
        webhook_url=config['discord']['webhook_url'],
        enabled=config['discord']['enabled']
    )
    
    # Init Strategy
    strategy = Coffin299Strategy(config, exchange, ai, discord)
    
    bot_state["strategy"] = strategy
    bot_state["exchange"] = exchange
    
    # Start Strategy Loop Task
    asyncio.create_task(run_strategy_loop(strategy))

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
    uvicorn.run(app, host=config['webui']['host'], port=config['webui']['port'])
