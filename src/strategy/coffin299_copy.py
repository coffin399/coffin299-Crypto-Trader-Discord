import asyncio
import aiohttp
from datetime import datetime, timedelta
from ..logger import setup_logger

logger = setup_logger("strategy_copy")

class Coffin299CopyStrategy:
    def __init__(self, config, exchange, ai, notifier):
        self.config = config
        self.exchange = exchange
        self.ai = ai
        self.notifier = notifier
        
        self.target_pair = "COPY_TRADING" # Virtual pair name
        self.current_recommendation = {"action": "COPY", "confidence": 1.0}
        
        self.top_traders = []
        self.last_leaderboard_update = datetime.min
        self.jpy_rate = 150.0 # Default fallback

        # Start background tasks
        asyncio.create_task(self.update_jpy_rate_loop())
        asyncio.create_task(self.periodic_report_loop())

    async def run_cycle(self):
        """
        Main copy strategy cycle.
        """
        logger.info("--- Strategy Cycle Start ---")
        
        # 1. Update Leaderboard (every 1 hour)
        if datetime.utcnow() - self.last_leaderboard_update > timedelta(hours=1):
            await self.update_leaderboard()
            
        if not self.top_traders:
            logger.warning("No top traders found to copy. Waiting...")
            return

        # Check copy mode
        copy_mode = self.config['strategy'].get('copy_trading', {}).get('copy_mode', 'aggregate')
        
        if copy_mode == 'mirror':
            await self.run_mirror_mode()
        else:
            await self.run_aggregate_mode()
    
    async def run_mirror_mode(self):
        """
        Mirror Mode: Copy ALL positions from a specific trader
        """
        logger.info("Running in MIRROR mode...")
        
        # Check if specific address is configured
        mirror_address = self.config['strategy'].get('copy_trading', {}).get('mirror_target_address', '')
        
        # Filter out placeholder addresses
        if mirror_address and mirror_address.startswith('0x') and len(mirror_address) > 10:
            target_trader = mirror_address
            logger.info(f"Using configured mirror address: {target_trader}")
        else:
            # Fallback to first trader from leaderboard
            if not self.top_traders:
                logger.warning("No traders available to mirror. Skipping.")
                return
            target_trader = self.top_traders[0]
            logger.info(f"Using leaderboard #1: {target_trader}")
        
        # Get target trader's positions
        target_positions = await self.exchange.get_user_positions(target_trader)
        logger.info(f"🔍 Target trader has {len(target_positions)} positions")
        for pos in target_positions:
            logger.info(f"  - {pos['symbol']}: {pos['side']} size={pos.get('size', 0)}")
        
        # Get our current positions
        my_positions = await self.exchange.get_positions()
        my_positions_dict = {p['symbol']: p for p in my_positions}
        
        # Fetch all prices once
        all_prices = {}
        if hasattr(self.exchange, 'get_all_prices'):
            all_prices = await self.exchange.get_all_prices()
        
        # Track symbols we should have positions in
        target_symbols = set()
        
        # Copy each position from target trader
        for pos in target_positions:
            symbol = pos['symbol']
            side = pos['side']  # LONG or SHORT
            target_symbols.add(symbol)
            
            # Filter by target coins if specified
            target_coins = self.config['strategy'].get('copy_trading', {}).get('target_coins', [])
            if target_coins and symbol not in target_coins:
                continue
            
            current_price = all_prices.get(symbol)
            
            # Execute trade to match this position
            action = "BUY" if side == "LONG" else "SELL"
            await self.execute_copy_trade(symbol, action, f"Mirroring {target_trader[:8]}...", price=current_price)
            
            await asyncio.sleep(0.1)
        
        # Close positions we have but target trader doesn't
        for symbol, my_pos in my_positions_dict.items():
            if symbol not in target_symbols:
                logger.info(f"Target trader closed {symbol}, closing our position...")
                # Close by trading opposite direction
                close_action = "SELL" if my_pos['side'] == 'LONG' else "BUY"
                current_price = all_prices.get(symbol)
                await self.execute_copy_trade(symbol, close_action, f"Closing {symbol} (not in target)", price=current_price)
                await asyncio.sleep(0.1)
    
    async def run_aggregate_mode(self):
        """
        Aggregate Mode: Use majority voting from multiple traders
        """
        logger.info("Running in AGGREGATE mode...")
        
        # 2. Analyze Top Traders' Positions
        aggregate_positions = {} # { 'ETH': {'LONG': 0, 'SHORT': 0} }
        
        for address in self.top_traders:
            positions = await self.exchange.get_user_positions(address)
            for pos in positions:
                symbol = pos['symbol']
                side = pos['side']
                
                if symbol not in aggregate_positions:
                    aggregate_positions[symbol] = {'LONG': 0, 'SHORT': 0}
                
                aggregate_positions[symbol][side] += 1
                
            await asyncio.sleep(0.5) # Reduced delay as we are more efficient now
            
        # 3. Decide & Execute
        target_coins = self.config['strategy'].get('copy_trading', {}).get('target_coins', [])
        min_concurrence = self.config['strategy'].get('copy_trading', {}).get('min_concurrence', 1)
        
        # Fetch all prices once to avoid rate limits
        all_prices = {}
        if hasattr(self.exchange, 'get_all_prices'):
            all_prices = await self.exchange.get_all_prices()
        
        for symbol, counts in aggregate_positions.items():
            # Filter by target coins if specified
            if target_coins and symbol not in target_coins:
                continue
                
            longs = counts['LONG']
            shorts = counts['SHORT']
            total = longs + shorts
            
            if total >= min_concurrence: 
                logger.info(f"Copy Signal for {symbol}: {longs} LONG vs {shorts} SHORT (Total: {total})")
                
                # Get price from cache or fetch if missing
                current_price = all_prices.get(symbol)
                
                # Simple Majority Vote
                if longs > shorts:
                    # BUY
                    await self.execute_copy_trade(symbol, "BUY", f"Copying {longs}/{total} top traders", price=current_price)
                elif shorts > longs:
                    # SELL
                    await self.execute_copy_trade(symbol, "SELL", f"Copying {shorts}/{total} top traders", price=current_price)
            
            # Sleep slightly even with bulk fetch to be safe
            await asyncio.sleep(0.1)

    async def update_leaderboard(self):
        logger.info("Updating Leaderboard...")
        
        new_traders = []
        # Try API
        if hasattr(self.exchange, 'get_leaderboard_top_traders'):
            new_traders = await self.exchange.get_leaderboard_top_traders(limit=self.config['strategy'].get('copy_trading', {}).get('leaderboard_limit', 5))
            
        if new_traders:
            self.top_traders = new_traders
            logger.info(f"Leaderboard Updated: {self.top_traders}")
        elif not self.top_traders:
            # Only use fallback if we have NO traders at all (first run or cleared)
            logger.warning("API Leaderboard fetch failed. Using fallback addresses.")
            fallback = self.config['strategy'].get('copy_trading', {}).get('fallback_addresses', [])
            self.top_traders = [addr for addr in fallback if addr and "0x..." not in addr]
        else:
             logger.warning("Leaderboard update failed, keeping previous traders.")
             
        self.last_leaderboard_update = datetime.utcnow()

    async def execute_copy_trade(self, symbol, side, reason, price=None):
        pair = f"{symbol}/USDC"
        
        # 1. Safety Margin Check
        safety_buffer_pct = self.config['strategy'].get('copy_trading', {}).get('safety_margin_buffer', 0.0)
        
        if safety_buffer_pct > 0:
            balance = await self.exchange.get_balance()
            total_equity = float(balance.get('total', {}).get('USDC', 0))
            free_margin = float(balance.get('free', {}).get('USDC', 0))
            
            safety_threshold = total_equity * safety_buffer_pct
            
            is_low_balance = free_margin < safety_threshold
            
            if is_low_balance:
                current_positions = await self.exchange.get_positions()
                my_pos = next((p for p in current_positions if p['symbol'] == symbol), None)
                
                if not my_pos:
                    logger.warning(f"Low Balance ({free_margin:.2f} < {safety_threshold:.2f}). Skipping OPEN trade for {pair}.")
                    return
                
                is_closing = (side == 'BUY' and my_pos['side'] == 'SHORT') or \
                             (side == 'SELL' and my_pos['side'] == 'LONG')

                if not is_closing:
                    logger.warning(f"Low Balance. Skipping trade that increases risk for {pair}.")
                    return
                else:
                    logger.info(f"Low Balance. Allowing CLOSING trade for {pair}.")

        # 2. Max Open Positions Check
        max_positions = self.config['strategy'].get('max_open_positions', 0)
        allow_short = self.config['strategy'].get('copy_trading', {}).get('allow_short', True)
        current_positions = await self.exchange.get_positions()
        my_pos = next((p for p in current_positions if p['symbol'] == symbol), None)

        # Logic for SELL (Shorting vs Closing)
        if side == "SELL":
            # If we have a LONG position, this SELL is a CLOSE/REDUCE -> Always Allowed
            if my_pos and my_pos['side'] == 'LONG' and my_pos['size'] > 0:
                pass # Allowed (Closing Long)
            
            # If we have NO position or a SHORT position, this SELL is a NEW SHORT or ADDING SHORT
            else:
                if not allow_short:
                    logger.info(f"Skipping SELL (Short) for {pair} because allow_short is False.")
                    return

        if max_positions > 0:
            # If we don't have a position, this is a new OPEN trade
            if not my_pos:
                if len(current_positions) >= max_positions:
                    logger.warning(f"Max Open Positions Reached ({len(current_positions)}/{max_positions}). Skipping OPEN trade for {pair}.")
                    return

        if not price or price <= 0:
            price = await self.exchange.get_market_price(pair)
            
        if not price or price <= 0:
            logger.error(f"Cannot execute trade for {pair}: Invalid Price {price}")
            return
        
        logger.info(f"EXECUTING COPY TRADE: {side} {pair} @ {price} ({reason})")
        
        order_side = side.lower()
        
        # Calculate Amount based on max_quantity (JPY)
        max_quantity_jpy = self.config['strategy'].get('copy_trading', {}).get('max_quantity', 1500)
        
        # 1. Convert JPY to USD
        usd_value = max_quantity_jpy / self.jpy_rate
        
        # 2. Convert USD to Token Amount (BEFORE checking duplicates)
        # Amount = USD / Price
        amount = usd_value / price
        
        # 🔵 デバッグ用ログ: 計算過程を記録
        logger.debug(f"Amount Calculation: max_quantity_jpy={max_quantity_jpy}, jpy_rate={self.jpy_rate}, usd_value={usd_value:.4f}, price={price}, amount={amount}")
        
        # Rounding - 8桁に変更（小額ポジションの精度向上）
        amount = round(amount, 8)
        
        if amount <= 0:
            logger.warning(f"❌ Calculated amount is too small or invalid: {amount} (JPY: {max_quantity_jpy}, Price: {price}, USD: {usd_value:.4f})")
            return
        
        # 3. 既に同方向のポジションを持っているかチェック
        if my_pos:
            current_side = my_pos['side'] # LONG or SHORT
            current_size = my_pos.get('size', 0)
            
            # ❌ サイズが0または無効な場合はポジションが実質的に存在しないため、重複チェックをスキップ
            if current_size <= 0:
                logger.debug(f"Position exists but size is 0 for {pair}, allowing trade.")
            # ✅ ロングポジションを既に持っていて、さらにBUYしようとしている場合
            elif side == 'BUY' and current_side == 'LONG':
                if current_size >= amount * 0.8: # 80% threshold for size
                    logger.info(f"Already have LONG position for {pair} (Size: {current_size:.8f} vs Target: {amount:.8f}). Skipping.")
                    return
            # ✅ ショートポジションを既に持っていて、さらにSELLしようとしている場合
            elif side == 'SELL' and current_side == 'SHORT':
                if current_size >= amount * 0.8:
                    logger.info(f"Already have SHORT position for {pair} (Size: {current_size:.8f} vs Target: {amount:.8f}). Skipping.")
                    return
        
        try:
            order = await self.exchange.create_order(pair, 'market', order_side, amount)
            if order:
                logger.info(f"Trade Executed: {order}")
                
                # Calculate JPY Value (Actual)
                total_jpy = amount * price * self.jpy_rate
                
                await self.notifier.notify_trade(side, pair, price, str(amount), reason, total_jpy=total_jpy)
            else:
                logger.error("Trade Execution Failed")
        except Exception as e:
            logger.error(f"Trade Execution Error: {e}")

    async def update_jpy_rate_loop(self):
        logger.info("Starting JPY Rate Polling Task...")
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            rate = data.get('rates', {}).get('JPY')
                            if rate:
                                self.jpy_rate = float(rate)
                                logger.info(f"Updated USD/JPY Rate: {self.jpy_rate}")
                            else:
                                logger.warning("JPY rate not found in API response")
                        else:
                            logger.warning(f"Failed to fetch exchange rate: {resp.status}")
            except Exception as e:
                logger.error(f"Error fetching exchange rate: {e}")
                
            await asyncio.sleep(3600) # 1 hour

    async def periodic_report_loop(self):
        logger.info("Starting Periodic Report Task (Every 30 mins)...")
        
        # Initial Report
        # Wait 10s to ensure WS prices are populated for accurate PnL
        await asyncio.sleep(10) 
        await self.send_report()
        
        while True:
            # Wait 30 minutes
            await asyncio.sleep(1800)
            await self.send_report()

    async def send_report(self):
        try:
            logger.info("🔵 Generating periodic report...")
            
            # Get balance
            balance = await self.exchange.get_balance()
            if not balance:
                logger.error("🔴 Failed to get balance - balance is empty")
                return
                
            total_usd = float(balance.get('total', {}).get('USDC', 0))
            total_jpy = total_usd * self.jpy_rate
            
            logger.info(f"Balance: ${total_usd:.2f} (¥{total_jpy:.0f})")
            
            # Get positions
            positions = await self.exchange.get_positions()
            if positions is None:
                logger.warning("🟡 get_positions returned None, using empty list")
                positions = []
            
            pos_summary = {}
            total_pnl_usd = 0.0
            
            for p in positions:
                try:
                    # Show Value if available, otherwise PnL
                    val = p.get('value', 0)
                    pnl = p.get('pnl', 0)
                    total_pnl_usd += pnl
                    
                    # Format: Size ($Value)
                    # Round size to 4 decimals, Value to 2 decimals
                    size_str = f"{p['size']:.4f}".rstrip('0').rstrip('.')
                    pos_summary[p['symbol']] = f"{size_str} (${val:.2f})"
                except Exception as e:
                    logger.error(f"🔴 Error processing position {p}: {e}")
                    continue
            
            total_pnl_jpy = total_pnl_usd * self.jpy_rate
            
            logger.info(f"PnL: ${total_pnl_usd:.2f} (¥{total_pnl_jpy:.0f}), Positions: {len(positions)}")
            
            # Send notification
            try:
                await self.notifier.notify_balance(
                    total_jpy, 
                    currency="JPY", 
                    changes=pos_summary,
                    total_pnl_usd=total_pnl_usd,
                    total_pnl_jpy=total_pnl_jpy
                )
                logger.info(f"🟢 Sent Periodic Report. Total: ${total_usd:.2f} (¥{total_jpy:.0f}), PnL: ${total_pnl_usd:.2f}")
            except Exception as e:
                logger.error(f"🔴 Failed to send balance notification: {e}")
                
        except Exception as e:
            logger.error(f"🔴 Error in periodic report: {e}", exc_info=True)

