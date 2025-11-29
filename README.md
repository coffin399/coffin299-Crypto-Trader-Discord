# Coffin299 Crypto Trader

A high-performance, AI-driven crypto trading bot designed for the 2025 bull run.
Optimized for **Hyperliquid** with Copy Trading and Real-time WebSocket support.

## 🚀 Key Features

*   **Hyperliquid Native**: Optimized for the Hyperliquid DEX (Perpetuals) with WebSocket price/position feed.
*   **Copy Trading (Mirror)**: Mirror the open positions of a top leaderboard wallet with configurable per-trade JPY risk.
*   **AI / GPT5.1 Strategy**: Multi-coin breakout strategy (`coffin299_GPT5.1`) with risk-per-trade, ATR-based sizing, and pyramiding.
*   **Real-time Data**: Uses WebSockets for millisecond-latency price updates and cached REST fallbacks.
*   **AI Analysis**: Integrates Google Gemini AI for higher-level market analysis (used by the original `coffin299` strategy).
*   **Paper Mode**: Risk-free simulation with persistent position tracking (SQLite).
*   **Discord Notifications**: Real-time trade alerts and periodic wallet/PnL reports.
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

### Recommended Setup 1: Hyperliquid Copy Trading (Mirror)

```yaml
active_exchange: "hyperliquid"

exchanges:
  hyperliquid:
    wallet_address: "YOUR_WALLET_ADDRESS"
    private_key: "YOUR_PRIVATE_KEY" # Leave empty for Paper Mode
    testnet: false

strategy:
  type: "copy_leaderboard"   # Enable Copy Trading (mirror mode)
  timeframe: "15m"
  max_open_positions: 0       # 0 = no limit
  loop_interval_seconds: 0    # Main loop interval (0 = as fast as possible)

  # Copy Trading Settings
  copy_trading:
    copy_mode: "mirror"       # "mirror" = mirror a single wallet, "aggregate" = majority vote
    leaderboard_limit: 5       # Fetch top N traders for fallback / aggregate
    mirror_target_address: "0x..."  # Wallet to mirror (empty = use leaderboard #1)
    target_coins: []           # Empty = copy all coins
    max_quantity: 500          # Max trade size in JPY per order (per symbol)
    safety_margin_buffer: 0.1  # If free margin < 10%, only allow closing trades
    allow_short: true          # Allow opening new SHORT positions

  # Paper Mode
  paper_mode:
    enabled: true              # Set to false for real trading
    initial_balance:
      ETH: 0.044               # ~20,000 JPY equivalent (auto-converts to USDC)
```

### Recommended Setup 2: GPT5.1 Multi-Coin Strategy

```yaml
active_exchange: "hyperliquid"

exchanges:
  hyperliquid:
    wallet_address: "YOUR_WALLET_ADDRESS"
    private_key: "YOUR_PRIVATE_KEY" # Leave empty for Paper Mode
    testnet: false

strategy:
  type: "coffin299_GPT5.1"    # Enable GPT5.1 breakout strategy
  timeframe: "15m"
  max_open_positions: 0        # 0 = unlimited symbols
  loop_interval_seconds: 0

  # GPT5.1 Strategy Settings
  gpt51_pair: "ETH/USDC"       # Fallback pair
  gpt51_universe:              # Symbols (without /USDC) to scan each cycle
    - "BTC"
    - "ETH"
    - "SOL"
    - "AVAX"
    - "BNB"
    - "LTC"
    - "DOGE"
    - "kPEPE"
    - "XRP"
    - "WLD"
    - "ADA"
    - "ENA"
    - "POPCAT"
    - "GOAT"
    - "HYPE"
    - "PENGU"
    - "PUMP"
    - "XPL"
    - "LINEA"
    - "ASTER"
  gpt51_base: "ETH"            # Base asset used for drawdown guard
  gpt51_risk_per_trade: 0.01   # Risk per trade as fraction of equity (e.g. 0.03 = 3%)
  gpt51_max_drawdown_pct: 0.5  # Stop opening new trades if ETH-equivalent equity drops 50%
  gpt51_breakout_lookback: 20  # Candles to look back for breakout
  gpt51_atr_multiplier: 2.0    # Stop distance = ATR * multiplier
  gpt51_max_pyramids: 3        # Max entries per symbol+side (pyramiding)

  paper_mode:
    enabled: true
    initial_balance:
      ETH: 0.044
```

## 🖥️ Usage

Run `run_bot.bat` to start the bot.
The bot runs in **Console Mode** and sends all updates to your configured Discord channels.

### Commands
*   `Ctrl+C`: Stop the bot safely.

## 📊 Strategy Modes

### 1. Copy Trading (`copy_leaderboard`)
- Uses Hyperliquid stats API to fetch top traders (7-day leaderboard).
- **Mirror mode**: mirror all open positions of a specific wallet (direction-only, fixed JPY size per trade).
- **Aggregate mode**: majority-vote across multiple top traders (optional).
- Position sizing is controlled via `copy_trading.max_quantity` (JPY per order).
- Supports both LONG and SHORT positions, with `safety_margin_buffer` to avoid over-leverage.

### 2. GPT5.1 Multi-Coin Strategy (`coffin299_GPT5.1`)
- Scans a configurable universe of symbols (e.g. BTC, ETH, SOL, memecoins) on Hyperliquid.
- Uses EMA-based trend detection + breakout over recent highs/lows.
- Risk-based position sizing using ATR and `gpt51_risk_per_trade` (e.g. 1–3% of equity per trade).
- Optional pyramiding (`gpt51_max_pyramids`) and ETH-equivalent drawdown guard (`gpt51_max_drawdown_pct`).
- Sends trade alerts and 30-minute balance/PnL reports to Discord.

### 3. AI Strategy (`coffin299`)
- Uses Google Gemini AI for market analysis and pair selection.
- Combines AI sentiment with technical indicators (RSI, EMA).
- Includes ML-based strategy learning (optional).
- Adaptive trading based on market conditions.

## 🔧 Recent Updates (2025-11-29)

### ✅ New
- Added **GPT5.1 Multi-Coin Strategy** (`coffin299_GPT5.1`) with:
  - EMA+ATR breakout logic
  - Risk-per-trade sizing and ETH-equivalent drawdown guard
  - Pyramiding control (`gpt51_max_pyramids`)

- Enhanced **Copy Trading Mirror Mode**:
  - Safer position/short checks and max-open-position guard
  - Per-trade JPY-based sizing via `copy_trading.max_quantity`
  - Discord trade alerts for all mirrored opens/closes

### ✅ Optimizations
- Hyperliquid OHLCV fetching now resolves CCXT symbols (e.g. `AVAX/USDC:USDC`) and caches responses to reduce rate limits.
- Added periodic 30-minute wallet/PnL reports for GPT5.1 and Copy strategies.

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
