    async def run_cycle(self):
        """
        Main copy strategy cycle.
        """
        # 1. Update Leaderboard (every 1 hour)
        if datetime.utcnow() - self.last_leaderboard_update > timedelta(hours=1):
            await self.update_leaderboard()
            
        if not self.top_traders:
            logger.warning("No top traders found to copy.")
            return

        # 2. Analyze Top Traders' Positions
        logger.info(f"Analyzing positions of {len(self.top_traders)} top traders: {self.top_traders}")
        
        aggregate_positions = {} # { 'ETH': {'LONG': 0, 'SHORT': 0} }
        
        for address in self.top_traders:
            positions = await self.exchange.get_user_positions(address)
            for pos in positions:
                symbol = pos['symbol']
                side = pos['side']
                
                if symbol not in aggregate_positions:
                    aggregate_positions[symbol] = {'LONG': 0, 'SHORT': 0}
                
                aggregate_positions[symbol][side] += 1
                
                aggregate_positions[symbol][side] += 1
                
            await asyncio.sleep(0.1) # Faster polling
            
        # 3. Decide & Execute
        # Logic: If > 50% of top traders are LONG on a coin, we LONG.
        
        target_coins = self.config['strategy'].get('copy_trading', {}).get('target_coins', [])
        min_concurrence = self.config['strategy'].get('copy_trading', {}).get('min_concurrence', 1)
        
        logger.info(f"Aggregated Positions: {aggregate_positions}")
        
        for symbol, counts in aggregate_positions.items():
            # Filter by target coins if specified
            if target_coins and symbol not in target_coins:
                continue
                
            longs = counts['LONG']
            shorts = counts['SHORT']
            total = longs + shorts
            
            if total >= min_concurrence: 
                logger.info(f"Copy Signal for {symbol}: {longs} LONG vs {shorts} SHORT (Total: {total})")
                
                # Simple Majority Vote
                if longs > shorts:
                    # BUY
                    await self.execute_copy_trade(symbol, "BUY", f"Copying {longs}/{total} top traders")
                elif shorts > longs:
                    # SELL
                    await self.execute_copy_trade(symbol, "SELL", f"Copying {shorts}/{total} top traders")

    async def update_leaderboard(self):
        logger.info("Updating Leaderboard...")
        
        # Try API
        if hasattr(self.exchange, 'get_leaderboard_top_traders'):
            self.top_traders = await self.exchange.get_leaderboard_top_traders(limit=self.config['strategy'].get('copy_trading', {}).get('leaderboard_limit', 5))
            
        # Fallback if empty
        if not self.top_traders:
            logger.warning("API Leaderboard fetch failed or empty. Using fallback addresses from config.")
            fallback = self.config['strategy'].get('copy_trading', {}).get('fallback_addresses', [])
            # Filter out placeholders
            self.top_traders = [addr for addr in fallback if addr and "0x..." not in addr]
            
        logger.info(f"Top Traders to Copy: {self.top_traders}")
        self.last_leaderboard_update = datetime.utcnow()

    async def execute_copy_trade(self, symbol, side, reason):
        pair = f"{symbol}/USDC"
        
        # 1. Safety Margin Check
        safety_buffer_pct = self.config['strategy'].get('copy_trading', {}).get('safety_margin_buffer', 0.0)
        
        if safety_buffer_pct > 0:
            balance = await self.exchange.get_balance()
            # Hyperliquid balance structure: {'total': {'USDC': ...}, 'free': {'USDC': ...}}
            total_equity = float(balance.get('total', {}).get('USDC', 0))
            free_margin = float(balance.get('free', {}).get('USDC', 0))
            
            safety_threshold = total_equity * safety_buffer_pct
            
            is_low_balance = free_margin < safety_threshold
            
            if is_low_balance:
                # Only allow trades that REDUCE risk (Close positions)
                # We need to know if we have a position in this symbol
                current_positions = await self.exchange.get_positions()
                # Find position for this symbol
                my_pos = next((p for p in current_positions if p['symbol'] == symbol), None)
                
                if not my_pos:
                    # No position, so this would be an OPEN trade. REJECT.
                    logger.warning(f"Low Balance ({free_margin:.2f} < {safety_threshold:.2f}). Skipping OPEN trade for {pair}.")
                    return
                
                # If we have a position, check if this trade closes it.
                # LONG signal -> Closes SHORT
                # SHORT signal -> Closes LONG
                
                is_closing = (side == 'LONG' and my_pos['side'] == 'SHORT') or \
                             (side == 'SELL' and my_pos['side'] == 'LONG') # side is BUY/SELL in execute_copy_trade call?
                             
                # Wait, execute_copy_trade receives 'BUY' or 'SELL' (from run_cycle)
                # run_cycle logic:
                # if longs > shorts: BUY
                # if shorts > longs: SELL
                
                # So:
                # BUY -> Long (Open Long or Close Short)
                # SELL -> Short (Open Short or Close Long)
                
                is_closing = (side == 'BUY' and my_pos['side'] == 'SHORT') or \
                             (side == 'SELL' and my_pos['side'] == 'LONG')

                if not is_closing:
                    logger.warning(f"Low Balance. Skipping trade that increases risk for {pair}.")
                    return
                else:
                    logger.info(f"Low Balance. Allowing CLOSING trade for {pair}.")

        price = await self.exchange.get_market_price(pair)
        
        # Mock execution for now (or call real execute if safe)
        # To be safe, we just log/notify in this first version
        logger.info(f"EXECUTING COPY TRADE: {side} {pair} @ {price} ({reason})")
        
        # Real execution
        # side is BUY/SELL. create_order expects 'buy'/'sell' (lowercase usually, but let's check BaseExchange)
        # BaseExchange checks 'buy'/'sell'.
        
        order_side = side.lower()
        amount = 0.01 # Fixed small amount for testing/safety. TODO: Calculate based on balance/risk.
        
        # For paper mode, we want to see positions.
        try:
            order = await self.exchange.create_order(pair, 'market', order_side, amount)
            if order:
                logger.info(f"Trade Executed: {order}")
                
                # Calculate JPY Value
                # Value = amount * price * self.jpy_rate
                total_jpy = amount * price * self.jpy_rate
                
                await self.notifier.notify_trade(side, pair, price, str(amount), reason, total_jpy=total_jpy)
            else:
                logger.error("Trade Execution Failed")
        except Exception as e:
            logger.error(f"Trade Execution Error: {e}")
