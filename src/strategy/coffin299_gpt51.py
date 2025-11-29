import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timedelta
from ..logger import setup_logger

logger = setup_logger("strategy_coffin299_gpt51")


class Coffin299GPT51Strategy:
    def __init__(self, config, exchange, ai_service, notifier):
        self.config = config
        self.exchange = exchange
        self.ai = ai_service
        self.notifier = notifier

        self.target_pair = config['strategy'].get('gpt51_pair', 'ETH/USDC')
        self.timeframe = config['strategy']['timeframe']

        self.universe = config['strategy'].get(
            'gpt51_universe',
            [
                'BTC',
                'ETH',
                'SOL',
                'AVAX',
                'BNB',
                'LTC',
                'DOGE',
                'kPEPE',
                'XRP',
                'WLD',
                'ADA',
                'ENA',
                'POPCAT',
                'GOAT',
                'HYPE',
                'PENGU',
                'PUMP',
                'XPL',
                'LINEA',
                'ASTER',
            ],
        )
        self.universe_index = 0

        self.base_symbol = config['strategy'].get('gpt51_base', 'ETH')
        self.start_base_equiv = None
        self.max_drawdown_pct = config['strategy'].get('gpt51_max_drawdown_pct', 0.5)

        self.last_report_time = datetime.utcnow()
        self.report_interval = timedelta(hours=1)

    async def run_cycle(self):
        now = datetime.utcnow()

        if now - self.last_report_time > self.report_interval:
            await self.report_status()
            self.last_report_time = now

        if not self.universe:
            pair = self.target_pair
        else:
            symbol = self.universe[self.universe_index % len(self.universe)]
            self.universe_index = (self.universe_index + 1) % len(self.universe)
            pair = f"{symbol}/USDC"

        await self.execute_trading_logic(pair)

    async def report_status(self):
        try:
            balance = await self.exchange.get_balance()
            total_usd = float(balance.get('total', {}).get('USDC', 0))

            try:
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    async with session.get("https://api.exchangerate-api.com/v4/latest/USD") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            usd_jpy = float(data.get('rates', {}).get('JPY', 150.0))
                        else:
                            usd_jpy = 150.0
            except Exception:
                usd_jpy = 150.0

            total_jpy = total_usd * usd_jpy

            positions = []
            if hasattr(self.exchange, 'get_positions'):
                try:
                    positions = await self.exchange.get_positions()
                except Exception as e:
                    logger.warning(f"Failed to get positions for report: {e}")

            changes = {}
            total_pnl_usd = 0.0
            for p in positions:
                pnl = p.get('pnl', 0)
                val = p.get('value', 0)
                total_pnl_usd += pnl
                size_str = f"{p['size']:.4f}".rstrip('0').rstrip('.')
                changes[p['symbol']] = f"{size_str} (${val:.2f})"

            total_pnl_jpy = total_pnl_usd * usd_jpy

            await self.notifier.notify_balance(
                total_jpy,
                "JPY",
                changes,
                total_pnl_usd=total_pnl_usd,
                total_pnl_jpy=total_pnl_jpy,
            )

            logger.info(
                f"GPT5.1 Report: Total=${total_usd:.2f} (¥{total_jpy:.0f}), PnL=${total_pnl_usd:.2f} (¥{total_pnl_jpy:.0f})"
            )
        except Exception as e:
            logger.error(f"Error in GPT5.1 report: {e}")

    async def execute_trading_logic(self, pair):
        ohlcv = await self.exchange.get_ohlcv(pair, self.timeframe, limit=200)
        if not ohlcv or len(ohlcv) < 100:
            return

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)

        df["ema_fast"] = df["close"].ewm(span=21, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=55, adjust=False).mean()

        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=14).mean()

        current = df.iloc[-1]
        price = float(current["close"])
        ema_fast = float(current["ema_fast"])
        ema_slow = float(current["ema_slow"])
        atr = float(current["atr"])

        if np.isnan(atr) or atr <= 0:
            return

        up_trend = price > ema_slow and ema_fast > ema_slow
        down_trend = price < ema_slow and ema_fast < ema_slow

        lookback = 20
        recent = df.iloc[-lookback:]
        breakout_long = up_trend and price >= recent["high"].max()
        breakout_short = down_trend and price <= recent["low"].min()

        positions = []
        if hasattr(self.exchange, "get_positions"):
            try:
                positions = await self.exchange.get_positions()
            except Exception as e:
                logger.warning(f"Failed to get positions in GPT5.1 logic: {e}")

        my_pos = next((p for p in positions if p["symbol"] == pair.split("/")[0]), None)

        if my_pos:
            side = my_pos["side"]
            size = my_pos["size"]

            if side == "LONG" and (not up_trend or breakout_short):
                await self.exchange.create_order(pair, "market", "sell", size, price)
                jpy_val = await self._calculate_jpy_value(pair, size, price)
                await self.notifier.notify_trade("SELL", pair, price, size, "Exit LONG", total_jpy=jpy_val)
                return

            if side == "SHORT" and (not down_trend or breakout_long):
                await self.exchange.create_order(pair, "market", "buy", size, price)
                jpy_val = await self._calculate_jpy_value(pair, size, price)
                await self.notifier.notify_trade("BUY", pair, price, size, "Exit SHORT", total_jpy=jpy_val)
                return

        max_positions = self.config["strategy"].get("max_open_positions", 0)
        if max_positions > 0:
            open_count = len(positions)
            if open_count >= max_positions and not my_pos:
                return

        if not breakout_long and not breakout_short:
            return

        balance = await self.exchange.get_balance()
        total_usd = float(balance.get("total", {}).get("USDC", 0))
        if total_usd <= 0:
            return

        can_open = await self._can_open_new_trade(total_usd)
        if not can_open:
            return

        risk_pct = self.config["strategy"].get("gpt51_risk_per_trade", 0.01)
        risk_usd = max(total_usd * risk_pct, 0)
        if risk_usd <= 0:
            return

        stop_distance = atr * 2.0
        if stop_distance <= 0:
            return

        size_by_risk = risk_usd / stop_distance
        max_size_1x = total_usd / price
        trade_size = min(size_by_risk, max_size_1x)

        if trade_size <= 0:
            return

        if breakout_long:
            order_side = "buy"
            notify_side = "BUY"
            reason = "GPT5.1 LONG breakout"
        else:
            order_side = "sell"
            notify_side = "SELL"
            reason = "GPT5.1 SHORT breakout"

        await self.exchange.create_order(pair, "market", order_side, trade_size, price)
        jpy_val = await self._calculate_jpy_value(pair, trade_size, price)
        await self.notifier.notify_trade(notify_side, pair, price, trade_size, reason, total_jpy=jpy_val)

    async def _can_open_new_trade(self, total_usd):
        try:
            base_pair = f"{self.base_symbol}/USDC"
            base_price = await self.exchange.get_market_price(base_pair)
            if not base_price or base_price <= 0:
                return True

            current_base_equiv = total_usd / base_price

            if self.start_base_equiv is None:
                self.start_base_equiv = current_base_equiv
                return True

            if self.max_drawdown_pct <= 0:
                return True

            min_base = self.start_base_equiv * (1.0 - self.max_drawdown_pct)
            if current_base_equiv < min_base:
                logger.warning(
                    f"ETH-equivalent balance below drawdown limit in GPT5.1. current={current_base_equiv:.6f}, min={min_base:.6f}"
                )
                return False

            return True
        except Exception as e:
            logger.warning(f"Failed to evaluate drawdown guard in GPT5.1: {e}")
            return True

    async def _calculate_jpy_value(self, pair, amount, price):
        try:
            base, quote = pair.split("/")
            val_in_quote = amount * price

            if quote == "JPY":
                return val_in_quote

            jpy_pair = f"{quote}/JPY"
            jpy_rate = await self.exchange.get_market_price(jpy_pair)
            return val_in_quote * jpy_rate
        except Exception as e:
            logger.warning(f"GPT5.1 failed to calculate JPY value: {e}")
            return None
