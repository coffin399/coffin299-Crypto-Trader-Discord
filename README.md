# Coffin299 Binance Trader

A high-frequency ETH/BTC circulation trading bot with Discord integration.

## Features
- **Strategy**: `coffin299strategy` (RSI + Bollinger Bands).
- **Circulation**: Trades ETH/BTC pair to accumulate both assets.
- **Notifications**: Beautiful Discord Embeds via a dedicated Discord Bot.
    - **Trades**: Sent to a specific Trade Channel.
    - **Summaries**: Sent to a specific Summary Channel.
- **Async Core**: Built with `asyncio` and `discord.py` for performance.
- **Safety**: Dry Run mode enabled by default.

## Setup

1. **Prerequisites**:
   - Python 3.11 installed.
   - A Discord Bot Token (create one at [Discord Developer Portal](https://discord.com/developers/applications)).
   - Two Discord Channels (one for trades, one for summaries) - get their IDs (Enable Developer Mode in Discord -> Right Click Channel -> Copy ID).

2. **Configuration**:
   - Edit `config.yaml`.
   - Add your **Binance API Key** and **Secret**.
   - Add your **Discord Bot Token**.
   - Add your **Trade Channel ID** and **Summary Channel ID**.
   - Adjust trading parameters if needed.

3. **Run**:
   Double-click `run_bot.bat` to start. It will automatically create a virtual environment, install dependencies, and run the bot.

## Strategy Details
- **Buy Signal**: Price touches Lower Bollinger Band AND RSI < 30.
- **Sell Signal**: Price touches Upper Bollinger Band AND RSI > 70.
- **Timeframe**: 1 minute (High Frequency).

## Disclaimer
This bot is for educational purposes. Use at your own risk.
