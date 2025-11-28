# Coffin299 Crypto Trader

A high-performance, AI-driven crypto trading bot designed for the 2025 bull run.
Now optimized for **Hyperliquid** with Copy Trading and Real-time WebSocket support.

## 🚀 Key Features

*   **Hyperliquid Native**: Optimized for the Hyperliquid DEX (Perpetuals).
*   **Copy Trading**: Automatically copy top traders from the Hyperliquid leaderboard.
*   **Real-time Data**: Uses WebSockets for millisecond-latency price updates.
*   **AI Analysis**: Integrates Google Gemini AI for market sentiment analysis (optional).
*   **Paper Mode**: Risk-free simulation with persistent position tracking (SQLite).
*   **Discord Notifications**: Get real-time alerts for trades and hourly wallet reports.

## 🛠 Prerequisites

*   **Python 3.11+**
*   **Hyperliquid Account** (Private Key required for real trading)
*   **Discord Bot Token** (for notifications)
*   **Google Gemini API Key** (for AI analysis)

## 📦 Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/your-repo/coffin299-trader.git
    cd coffin299-trader
    ```

2.  **Run the setup script**
    Double-click `run_bot.bat`.
    This will create a virtual environment, install dependencies, and start the bot.

3.  **Configuration**
    The first run will generate a `config.yaml` file from `config.default.yaml`.
    Edit `config.yaml` with your settings.

## ⚙️ Configuration Guide (`config.yaml`)

### Recommended Setup (Hyperliquid Copy Trading)

```yaml
active_exchange: "hyperliquid"

exchanges:
  hyperliquid:
    wallet_address: "YOUR_WALLET_ADDRESS"
    private_key: "YOUR_PRIVATE_KEY" # Leave empty for Paper Mode
    testnet: false

strategy:
  type: "copy_leaderboard" # Enable Copy Trading
  copy_trading:
    leaderboard_limit: 5      # Copy top 5 traders
    target_coins: []          # Empty = Copy all coins they trade
    max_quantity: 500         # Max trade size in JPY per order
    allow_short: true         # Enable shorting (Recommended)
  
  paper_mode:
    enabled: true             # Set to false for Real Trading
```

## 🖥️ Usage

Run `run_bot.bat` to start the bot.
The bot runs in **Console Mode** and sends all updates to your configured Discord channels.

### Commands
*   `Ctrl+C`: Stop the bot safely.

## ⚠️ Risk Warning

*   **Cryptocurrency trading involves significant risk.**
*   **Copy Trading** does not guarantee profits. Top traders can lose money.
*   **Paper Mode** is recommended for testing strategies before risking real funds.
*   Use this software at your own risk. The developers are not responsible for any financial losses.

## 📝 License

MIT License
