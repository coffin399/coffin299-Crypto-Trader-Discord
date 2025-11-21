import asyncio
import yaml
import logging
import datetime
import os
import discord
import webbrowser
import uvicorn
from discord.ext import tasks, commands
from dotenv import load_dotenv

from utils.binance_client import BinanceClient
from utils.discord_notify import DiscordEmbedGenerator
from strategies.coffin299 import Coffin299Strategy
from web.server import app, broadcast_update

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BinanceTrader")

def load_config():
    if not os.path.exists('config.yaml'):
        if os.path.exists('config.default.yaml'):
            import shutil
            shutil.copy('config.default.yaml', 'config.yaml')
            logger.info("Created config.yaml from default. Please edit it.")
        else:
            logger.error("config.default.yaml not found!")
            exit(1)
            
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

config = load_config()
load_dotenv()

# Discord Bot Setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Global State
binance = None
strategy = None
last_summary_time = datetime.datetime.now()
last_hour_value_jpy = 0
start_value_jpy = 0
initial_setup_done = False

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    if not trading_loop.is_running():
        trading_loop.start()

@tasks.loop(seconds=config['system']['check_interval'])
async def trading_loop():
    global last_summary_time, last_hour_value_jpy, start_value_jpy, initial_setup_done, binance, strategy

    try:
        if not strategy:
            strategy = Coffin299Strategy(
                ema_fast=config['trading']['strategy']['ema_fast'],
                ema_slow=config['trading']['strategy']['ema_slow'],
                stoch_k=config['trading']['strategy']['stoch_k'],
                stoch_d=config['trading']['strategy']['stoch_d'],
                stoch_rsi=config['trading']['strategy']['stoch_rsi'],
                stoch_window=config['trading']['strategy']['stoch_window'],
                overbought=config['trading']['strategy']['overbought'],
                oversold=config['trading']['strategy']['oversold']
            )

        if not binance:
            try:
                temp_binance = BinanceClient(
                    config['binance']['api_key'],
                    config['binance']['api_secret'],
                    testnet=config['binance']['testnet'],
                    paper_trading=config['trading']['dry_run'],
                    paper_initial_btc=config['trading'].get('dry_run_initial_capital_btc', 0.00076865)
                )
                await temp_binance.initialize()
                binance = temp_binance
            except Exception as e:
                logger.error(f"Failed to initialize Binance Client: {e}")
                await asyncio.sleep(5) # Wait before retrying
                return # Skip this iteration

        symbol = config['trading']['symbol']
        base_currency = symbol.split('/')[0]
        quote_currency = symbol.split('/')[1]
        trade_amount_jpy = config['trading']['trade_amount_jpy']
        dry_run = config['trading']['dry_run']

        # Helper to get BTC/JPY price
        async def get_btc_jpy_price():
            ticker = await binance.get_ticker("BTC/JPY")
            if ticker:
                return ticker['last']
            
            # Fallback to BTC/USDT * 155
            ticker_usdt = await binance.get_ticker("BTC/USDT")
            if ticker_usdt:
                return ticker_usdt['last'] * 155.0
            
            return 0.0

        # Initial Value Setup (Run once)
        if not initial_setup_done:
            btc_jpy = await get_btc_jpy_price()
            
            eth_bal, _ = await binance.get_balance(base_currency)
            btc_bal, _ = await binance.get_balance(quote_currency)
            ticker = await binance.get_ticker(symbol)
            current_price = ticker['last'] if ticker else 0
            
            total_btc_value = (eth_bal * current_price) + btc_bal
            start_value_jpy = total_btc_value * btc_jpy
            last_hour_value_jpy = start_value_jpy
            initial_setup_done = True
            logger.info(f"Initial Value: ¥{start_value_jpy:,.0f} (BTC/JPY: {btc_jpy:,.0f})")

            # Send Startup Summary
            mode_str = "Dry Run (Paper)" if dry_run else "Live Trading"
            embed = DiscordEmbedGenerator.create_wallet_summary_embed(
                start_value_jpy, 0, 0, title=f"🚀 Bot Started ({mode_str})"
            )
            channel = bot.get_channel(config['discord']['summary_channel_id'])
            if channel:
                await channel.send(embed=embed)
            else:
                logger.error("Summary Channel ID not found or bot cannot access it.")

        # Broadcast Status Update
        if initial_setup_done:
            ticker = await binance.get_ticker(symbol)
            current_price = ticker['last']
            btc_jpy = await get_btc_jpy_price()
            
            eth_bal, _ = await binance.get_balance(base_currency)
            btc_bal, _ = await binance.get_balance(quote_currency)
            
            current_total_btc = (eth_bal * current_price) + btc_bal
            current_value_jpy = current_total_btc * btc_jpy
            total_change = current_value_jpy - start_value_jpy

            await broadcast_update({
                "type": "status",
                "payload": {
                    "total_value_jpy": current_value_jpy,
                    "total_change_jpy": total_change
                }
            })

        # 1. Time Check for Hourly Summary
        now = datetime.datetime.now()
        if (now - last_summary_time).total_seconds() >= 3600:
            ticker = await binance.get_ticker(symbol)
            current_price = ticker['last']
            btc_jpy = await get_btc_jpy_price()
            
            eth_bal, _ = await binance.get_balance(base_currency)
            btc_bal, _ = await binance.get_balance(quote_currency)
            
            current_total_btc = (eth_bal * current_price) + btc_bal
            current_value_jpy = current_total_btc * btc_jpy
            
            change_1h = current_value_jpy - last_hour_value_jpy
            total_change = current_value_jpy - start_value_jpy
            
            embed = DiscordEmbedGenerator.create_wallet_summary_embed(current_value_jpy, change_1h, total_change)
            channel = bot.get_channel(config['discord']['summary_channel_id'])
            if channel:
                await channel.send(embed=embed)
            else:
                logger.error("Summary Channel ID not found or bot cannot access it.")
            
            last_summary_time = now
            last_hour_value_jpy = current_value_jpy
            logger.info("Sent Hourly Summary")

        # 2. Trading Logic
        df = await binance.get_ohlcv(symbol, timeframe=config['trading']['timeframe'])
        
        # Broadcast Candle
        if not df.empty:
            last_candle = df.iloc[-1]
            await broadcast_update({
                "type": "candle",
                "payload": {
                    "time": int(last_candle['timestamp'].timestamp()),
                    "open": last_candle['open'],
                    "high": last_candle['high'],
                    "low": last_candle['low'],
                    "close": last_candle['close']
                }
            })

        signal = strategy.analyze(df)
        
        if signal:
            logger.info(f"Signal Detected: {signal}")
            
            eth_bal, eth_free = await binance.get_balance(base_currency)
            btc_bal, btc_free = await binance.get_balance(quote_currency)
            ticker = await binance.get_ticker(symbol)
            current_price = ticker['last']
            btc_jpy = await get_btc_jpy_price()

            target_amount_btc = trade_amount_jpy / btc_jpy
            amount_eth = target_amount_btc / current_price

            executed = False
            logger.info(f"Balances - BTC: {btc_free:.6f}, ETH: {eth_free:.6f}")
            if signal == 'BUY':
                cost_btc = amount_eth * current_price
                if btc_free > cost_btc:
                    logger.info(f"Attempting to BUY {amount_eth} {base_currency}")
                    order = await binance.create_order(symbol, 'buy', amount_eth)
                    if order: executed = True
                else:
                    logger.warning("Insufficient BTC for BUY")

            elif signal == 'SELL':
                if eth_free > amount_eth:
                    logger.info(f"Attempting to SELL {amount_eth} {base_currency}")
                    order = await binance.create_order(symbol, 'sell', amount_eth)
                    if order: executed = True
                else:
                    # Only log warning if we haven't logged it recently (optional, but for now just debug)
                    logger.debug("Insufficient ETH for SELL")
            
            if executed:
                embed = DiscordEmbedGenerator.create_trade_embed(signal, symbol, current_price, amount_eth, trade_amount_jpy, "coffin299")
                channel = bot.get_channel(config['discord']['trade_channel_id'])
                if channel:
                    await channel.send(embed=embed)
                else:
                    logger.error("Trade Channel ID not found or bot cannot access it.")
                
                # Broadcast Trade
                await broadcast_update({
                    "type": "trade",
                    "payload": {
                        "side": signal,
                        "symbol": symbol,
                        "price": current_price
                    }
                })

    except Exception as e:
        logger.error(f"Error in trading loop: {e}")

@trading_loop.before_loop
async def before_trading_loop():
    await bot.wait_until_ready()

@app.get("/api/history")
async def get_history():
    global binance, config
    if not binance:
        return []
    
    try:
        symbol = config['trading']['symbol']
        timeframe = config['trading']['timeframe']
        # Fetch last 100 candles
        df = await binance.get_ohlcv(symbol, timeframe=timeframe, limit=100)
        
        if df.empty:
            return []
            
        candles = []
        for _, row in df.iterrows():
            candles.append({
                "time": int(row['timestamp'].timestamp()),
                "open": row['open'],
                "high": row['high'],
                "low": row['low'],
                "close": row['close']
            })
        return candles
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return []

async def main():
    # Start Web Server in background
    config_uvicorn = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config_uvicorn)
    
    # Open Browser
    webbrowser.open("http://localhost:8000")
    logger.info("Opened WebGUI in browser")

    async with bot:
        # Run both Bot and Web Server
        await asyncio.gather(
            bot.start(config['discord']['token']),
            server.serve()
        )

if __name__ == "__main__":
    try:
        # Fix for Windows Event Loop Policy if needed
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
