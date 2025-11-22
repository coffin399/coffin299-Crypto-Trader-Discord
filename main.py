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

from utils.hyperliquid_client import HyperliquidClient
from utils.discord_notify import DiscordEmbedGenerator
from strategies.coffin299 import HyperTrendStrategy
from web.server import app, broadcast_update

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HyperTrader")

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
exchange = None
strategy = None
last_summary_time = datetime.datetime.now()
last_hour_value_usd = 0
start_value_usd = 0
initial_setup_done = False

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    if not trading_loop.is_running():
        trading_loop.start()

@tasks.loop(seconds=config['system']['check_interval'])
async def trading_loop():
    global last_summary_time, last_hour_value_usd, start_value_usd, initial_setup_done, exchange, strategy

    try:
        if not strategy:
            s_conf = config['trading']['strategy']
            strategy = HyperTrendStrategy(
                ema_fast=s_conf['ema_fast'],
                ema_slow=s_conf['ema_slow'],
                macd_signal=s_conf['macd_signal'],
                atr_period=s_conf['atr_period'],
                atr_multiplier_sl=s_conf['atr_multiplier_sl'],
                atr_multiplier_tp=s_conf['atr_multiplier_tp'],
                rsi_period=s_conf['rsi_period'],
                rsi_overbought=s_conf['rsi_overbought'],
                rsi_oversold=s_conf['rsi_oversold']
            )

        if not exchange:
            try:
                temp_exchange = HyperliquidClient(
                    config['hyperliquid']['wallet_address'],
                    config['hyperliquid']['wallet_private_key'],
                    testnet=config['hyperliquid']['testnet'],
                    paper_trading=config['trading']['dry_run'],
                    paper_initial_usd=config['trading'].get('dry_run_initial_capital_usd', 10000)
                )
                await temp_exchange.initialize()
                exchange = temp_exchange
            except Exception as e:
                logger.error(f"Failed to initialize Hyperliquid Client: {e}")
                await asyncio.sleep(5) # Wait before retrying
                return # Skip this iteration

        symbol = config['trading']['symbol']
        trade_amount_usd = config['trading']['trade_amount_usd']
        dry_run = config['trading']['dry_run']

        # Initial Value Setup (Run once)
        if not initial_setup_done:
            total_bal, free_bal = await exchange.get_balance_usdc()
            # For Perps, we should also check unrealized PnL if possible, but for now start with Balance
            start_value_usd = total_bal
            last_hour_value_usd = start_value_usd
            initial_setup_done = True
            logger.info(f"Initial Value: ${start_value_usd:,.2f} USDC")

            # Send Startup Summary
            mode_str = "Dry Run (Paper)" if dry_run else "Live Trading"
            embed = DiscordEmbedGenerator.create_wallet_summary_embed(
                start_value_usd, 0, 0, title=f"🚀 Bot Started ({mode_str})"
            )
            channel = bot.get_channel(config['discord']['summary_channel_id'])
            if channel:
                await channel.send(embed=embed)
            else:
                logger.error("Summary Channel ID not found or bot cannot access it.")

        # Broadcast Status Update
        if initial_setup_done:
            total_bal, free_bal = await exchange.get_balance_usdc()
            current_value_usd = total_bal
            total_change = current_value_usd - start_value_usd
            
            # Get current position for UI
            position = await exchange.get_position(symbol)
            pos_data = None
            if position:
                pos_data = {
                    "symbol": position['symbol'],
                    "size": position['size'],
                    "entryPrice": position['entryPrice'],
                    "unrealizedPnL": position.get('unrealizedPnL', 0),
                    "leverage": position.get('leverage', 1)
                }

            await broadcast_update({
                "type": "status",
                "payload": {
                    "total_value_usd": current_value_usd,
                    "total_change_usd": total_change,
                    "position": pos_data
                }
            })

        # 1. Time Check for Hourly Summary
        now = datetime.datetime.now()
        if (now - last_summary_time).total_seconds() >= 3600:
            total_bal, _ = await exchange.get_balance_usdc()
            current_value_usd = total_bal
            
            change_1h = current_value_usd - last_hour_value_usd
            total_change = current_value_usd - start_value_usd
            
            embed = DiscordEmbedGenerator.create_wallet_summary_embed(current_value_usd, change_1h, total_change)
            channel = bot.get_channel(config['discord']['summary_channel_id'])
            if channel:
                await channel.send(embed=embed)
            
            last_summary_time = now
            last_hour_value_usd = current_value_usd
            logger.info("Sent Hourly Summary")

        # 2. Trading Logic
        df = await exchange.get_ohlcv(symbol, timeframe=config['trading']['timeframe'])
        
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

        signal_data = strategy.analyze(df)
        
        if signal_data:
            signal = signal_data['signal']
            logger.info(f"Signal Detected: {signal}")
            
            total_bal, free_bal = await exchange.get_balance_usdc()
            ticker = await exchange.get_ticker(symbol)
            if not ticker:
                logger.error(f"Failed to get ticker for {symbol}. Skipping cycle.")
                return

            current_price = ticker['last']
            
            # Check current position
            position = await exchange.get_position(symbol)
            current_pos_size = position['size'] if position else 0
            
            # Logic for Open/Close
            executed = False
            amount_to_trade = 0
            
            if signal == 'BUY':
                # If we are Short, Close Short first (Buy)
                if current_pos_size < 0:
                    logger.info(f"Closing SHORT position of {abs(current_pos_size)}")
                    await exchange.create_order(symbol, 'buy', abs(current_pos_size))
                    current_pos_size = 0 # Assumed closed
                
                # Open Long if not already Long
                if current_pos_size == 0:
                    amount_usd = trade_amount_usd
                    amount_token = amount_usd / current_price
                    if free_bal > amount_usd: # Simple check
                        logger.info(f"Opening LONG: {amount_token} {symbol}")
                        order = await exchange.create_order(symbol, 'buy', amount_token)
                        if order: executed = True
                    else:
                        logger.warning("Insufficient USDC for Long")

            elif signal == 'SELL':
                # If we are Long, Close Long first (Sell)
                if current_pos_size > 0:
                    logger.info(f"Closing LONG position of {current_pos_size}")
                    await exchange.create_order(symbol, 'sell', current_pos_size)
                    current_pos_size = 0 # Assumed closed
                
                # Open Short if not already Short (and if strategy allows shorting)
                if current_pos_size == 0:
                    amount_usd = trade_amount_usd
                    amount_token = amount_usd / current_price
                    if free_bal > amount_usd:
                        logger.info(f"Opening SHORT: {amount_token} {symbol}")
                        order = await exchange.create_order(symbol, 'sell', amount_token)
                        if order: executed = True
                    else:
                        logger.warning("Insufficient USDC for Short")
            
            if executed:
                embed = DiscordEmbedGenerator.create_trade_embed(signal, symbol, current_price, amount_to_trade, trade_amount_usd, "HyperTrend")
                channel = bot.get_channel(config['discord']['trade_channel_id'])
                if channel:
                    await channel.send(embed=embed)
                
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
    pass

@app.get("/api/history")
async def get_history():
    global exchange, config
    if not exchange:
        return []
    
    try:
        symbol = config['trading']['symbol']
        timeframe = config['trading']['timeframe']
        df = await exchange.get_ohlcv(symbol, timeframe=timeframe, limit=100)
        
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

async def run_discord_bot():
    while True:
        try:
            await bot.start(config['discord']['token'])
        except Exception as e:
            logger.error(f"Discord connection error: {e}. Retrying in 30s...")
            await asyncio.sleep(30)

async def main():
    # Start Web Server in background
    config_uvicorn = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config_uvicorn)
    
    # Open Browser
    webbrowser.open("http://localhost:8000")
    logger.info("Opened WebGUI in browser")

    # Start Trading Loop explicitly
    if not trading_loop.is_running():
        trading_loop.start()

    # Run both Bot (Robust) and Web Server
    await asyncio.gather(
        run_discord_bot(),
        server.serve()
    )

if __name__ == "__main__":
    try:
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
