# Coffin299 Crypto Trader

A high-performance, AI-driven crypto trading bot designed for the 2025 bull run.
Optimized for **Hyperliquid** with Copy Trading and Real-time WebSocket support.

## 🚀 Key Features

*   **Hyperliquid Native**: Optimized for the Hyperliquid DEX (Perpetuals).
*   **Copy Trading**: Automatically copy top traders from the Hyperliquid leaderboard.
*   **Real-time Data**: Uses WebSockets for millisecond-latency price updates.
*   **AI Analysis**: Integrates Google Gemini AI for market sentiment analysis (optional).
*   **Paper Mode**: Risk-free simulation with persistent position tracking (SQLite).
*   **Discord Notifications**: Get real-time alerts for trades and hourly wallet reports.
*   **Multi-Exchange Support**: Hyperliquid, Trade.xyz, Tread.fi

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
  max_open_positions: 10
  
  copy_trading:
    leaderboard_limit: 5      # Copy top 5 traders
    min_concurrence: 3        # Minimum 3 traders must hold a position to copy it
    target_coins: []          # Empty = Copy all coins they trade
    max_quantity: 500         # Max trade size in JPY per order
    safety_margin_buffer: 0.1 # Keep 10% margin for safety (only close trades when low)
    allow_short: true         # Enable shorting (Recommended for futures)
  
  paper_mode:
    enabled: true             # Set to false for Real Trading
    initial_balance:
      ETH: 0.044              # ~20,000 JPY equivalent (auto-converts to USDC)
```

## 🖥️ Usage

Run `run_bot.bat` to start the bot.
The bot runs in **Console Mode** and sends all updates to your configured Discord channels.

### Commands
*   `Ctrl+C`: Stop the bot safely.

## 📊 Strategy Modes

### 1. Copy Trading (`copy_leaderboard`)
- Fetches top traders from Hyperliquid leaderboard (7-day performance)
- Analyzes their open positions in real-time
- Uses majority voting: if 3+ traders are LONG on ETH, bot goes LONG
- Automatically manages position sizing based on `max_quantity` (JPY)
- Supports both LONG and SHORT positions

### 2. AI Strategy (`coffin299`)
- Uses Google Gemini AI for market analysis
- Combines AI sentiment with technical indicators (RSI, EMA)
- Includes ML-based strategy learning (optional)
- Adaptive trading based on market conditions

## 🔧 Recent Updates (2025-11-28)

### ✅ Bug Fixes
- 🔴 **CRITICAL**: Fixed Paper Mode SHORT position detection bug
  - SHORT positions are now correctly identified (was always showing as LONG)
  - Prevents duplicate SHORT orders
  
- 🔴 **CRITICAL**: Improved position duplicate check logic
  - Changed from value-based to size-based checking
  - Prevents unintended additional orders due to price fluctuations
  - Threshold tightened from 90% to 80%

### ✅ Optimizations
- `min_concurrence` default changed from 1 to 3 (reduces noise trades)
- Enhanced logging for position skip reasons
- Removed Binance Japan support (inaccessible from Japan)

## ⚠️ Risk Warning

*   **Cryptocurrency trading involves significant risk.**
*   **Copy Trading** does not guarantee profits. Top traders can lose money.
*   **Leverage Trading** can amplify both gains and losses.
*   **Paper Mode** is strongly recommended for testing strategies before risking real funds.
*   Always set appropriate `max_quantity` and `max_open_positions` limits.
*   Use `safety_margin_buffer` to prevent liquidation.
*   Use this software at your own risk. The developers are not responsible for any financial losses.

## 🐛 Troubleshooting

### Bot crashes on startup
- Check that `config.yaml` exists and has valid settings
- Ensure Python 3.11+ is installed
- Verify Discord bot token and channel IDs

### No trades executing
- Verify `active_exchange` matches your intended exchange
- Check that `paper_mode.enabled` is set correctly
- For Copy Trading: ensure `min_concurrence` isn't too high (try 2-3)
- Check Discord logs for error messages

### WebSocket connection issues
- Hyperliquid WebSocket auto-reconnects every 5 seconds on failure
- Check your internet connection
- Verify `testnet` setting matches your wallet

## 📝 License

MIT License
