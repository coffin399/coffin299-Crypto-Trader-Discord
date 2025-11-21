# Coffin299 Binance Trader

A high-frequency ETH/BTC circulation trading bot with Discord integration and a modern WebGUI.

## Features
- **Strategy**: `coffin299strategy` (RSI + Bollinger Bands).
- **Circulation**: Trades ETH/BTC pair to accumulate both assets.
- **WebGUI**: Real-time dashboard on `http://localhost:8000`.
- **Notifications**: Beautiful Discord Embeds via a dedicated Discord Bot.
    - **Trades**: Sent to a specific Trade Channel.
    - **Summaries**: Sent to a specific Summary Channel.
- **Async Core**: Built with `asyncio` and `discord.py` for performance.
- **Safety**: Dry Run mode enabled by default.

## Setup

1. **Prerequisites**:
   - Python 3.11 installed.
   - A Discord Bot Token.
   - Two Discord Channels (Trade & Summary).

2. **Configuration**:
   - Edit `config.yaml` (copied from `config.default.yaml` on first run).
   - Add your **Binance API Key** and **Secret**.
   - Add your **Discord Bot Token**.
   - Add your **Trade Channel ID** and **Summary Channel ID**.

3. **Run**:
   Double-click `run_bot.bat` to start.
   - **Bot**: Starts trading and sending Discord notifications.
   - **WebGUI**: Opens at `http://localhost:8000`.

## Strategy Details
- **Buy Signal**: Price touches Lower Bollinger Band AND RSI < 30.
- **Sell Signal**: Price touches Upper Bollinger Band AND RSI > 70.
- **Timeframe**: 1 minute (High Frequency).

## Disclaimer
This bot is for educational purposes. Use at your own risk.
