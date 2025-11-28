import discord
import asyncio
from datetime import datetime, timedelta
from ..logger import setup_logger

logger = setup_logger("discord_bot")

class DiscordNotifier:
    def __init__(self, config):
        self.enabled = config['discord']['enabled']
        self.token = config['discord'].get('bot_token')
        self.channels = config['discord'].get('channels', {})
        
        self.client = None
        self.notification_buffer = []
        self._connection_task = None
        self._flush_task = None
        self._health_check_task = None
        self._is_shutting_down = False
        self._last_successful_send = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        
        if self.enabled and self.token:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Discord client with event handlers."""
        intents = discord.Intents.default()
        self.client = discord.Client(intents=intents)
        
        @self.client.event
        async def on_ready():
            logger.info(f"🟢 Discord Bot logged in as {self.client.user}")
            self._reconnect_attempts = 0
            self._last_successful_send = datetime.utcnow()
        
        @self.client.event
        async def on_disconnect():
            if not self._is_shutting_down:
                logger.warning("🟡 Discord Bot disconnected")
        
        @self.client.event
        async def on_resumed():
            logger.info("🟢 Discord Bot connection resumed")
            self._reconnect_attempts = 0

    async def start(self):
        """
        Starts the Discord client in the background with monitoring.
        """
        if self.client and self.token:
            try:
                # Start the client without blocking
                self._connection_task = asyncio.create_task(self._managed_client_start())
                # Start buffer flush loop
                self._flush_task = asyncio.create_task(self._flush_buffer_loop())
                # Start health check
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                logger.info("🔵 Discord Bot started with monitoring")
            except Exception as e:
                logger.error(f"🔴 Failed to start Discord bot: {e}")

    async def _managed_client_start(self):
        """Managed start with automatic reconnection."""
        while not self._is_shutting_down:
            try:
                logger.info("🔵 Starting Discord client connection...")
                await self.client.start(self.token)
            except discord.errors.LoginFailure as e:
                logger.error(f"🔴 Discord login failed (invalid token): {e}")
                break
            except Exception as e:
                self._reconnect_attempts += 1
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    logger.error(f"🔴 Max reconnection attempts ({self._max_reconnect_attempts}) reached. Stopping.")
                    break
                
                wait_time = min(60, 5 * self._reconnect_attempts)
                logger.error(f"🟡 Discord client error (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}): {e}")
                logger.info(f"🔵 Reconnecting in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                
                # Reinitialize client for clean reconnection
                if not self.client.is_closed():
                    await self.client.close()
                self._initialize_client()

    async def _health_check_loop(self):
        """Periodic health check to detect silent failures."""
        while not self._is_shutting_down:
            await asyncio.sleep(60)  # Check every 60 seconds
            
            try:
                if self.client and self.client.is_ready():
                    # Check if we haven't sent anything for too long
                    if self._last_successful_send:
                        time_since_last_send = datetime.utcnow() - self._last_successful_send
                        if time_since_last_send > timedelta(minutes=30):
                            logger.warning(f"🟡 No successful sends in {time_since_last_send.total_seconds()/60:.1f} minutes")
                    
                    # Verify we can still fetch a channel
                    test_channel_key = list(self.channels.keys())[0] if self.channels else None
                    if test_channel_key:
                        channel = await self._get_channel(test_channel_key)
                        if channel:
                            logger.debug(f"🟢 Health check passed - channel {test_channel_key} accessible")
                        else:
                            logger.warning(f"🟡 Health check warning - cannot access channel {test_channel_key}")
                else:
                    logger.warning(f"🟡 Health check failed - client not ready (is_closed: {self.client.is_closed() if self.client else 'N/A'})")
            except Exception as e:
                logger.error(f"🔴 Health check error: {e}")

    async def _flush_buffer_loop(self):
        """Flush notification buffer with error recovery."""
        while not self._is_shutting_down:
            try:
                await asyncio.sleep(3)
                if self.notification_buffer:
                    # Flush buffer
                    to_send = self.notification_buffer[:]
                    self.notification_buffer = []
                    
                    channel_key = 'trade_alerts'
                    channel = await self._get_channel(channel_key)
                    
                    if channel:
                        # Chunk into groups of 10 (Discord limit per message)
                        for i in range(0, len(to_send), 10):
                            chunk = to_send[i:i+10]
                            try:
                                await channel.send(embeds=chunk)
                                self._last_successful_send = datetime.utcnow()
                            except Exception as e:
                                logger.error(f"🔴 Failed to send buffered embeds: {e}")
                                # Re-add failed chunks to buffer
                                self.notification_buffer.extend(chunk)
                    else:
                        # Channel not available, put messages back
                        logger.warning(f"🟡 Channel not available, re-buffering {len(to_send)} notifications")
                        self.notification_buffer = to_send + self.notification_buffer
            except Exception as e:
                logger.error(f"🔴 Error in flush buffer loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def shutdown(self):
        """Gracefully shutdown the Discord bot."""
        logger.info("🔵 Shutting down Discord bot...")
        self._is_shutting_down = True
        
        # Cancel background tasks
        for task in [self._health_check_task, self._flush_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close client
        if self.client and not self.client.is_closed():
            await self.client.close()
        
        logger.info("🟢 Discord bot shutdown complete")

    async def _get_channel(self, channel_key):
        if not self.client or not self.client.is_ready():
            return None
            
        channel_id = self.channels.get(channel_key)
        if not channel_id:
            logger.error(f"🔴 Channel ID for '{channel_key}' not configured.")
            return None
            
        try:
            channel = self.client.get_channel(int(channel_id))
            if not channel:
                channel = await self.client.fetch_channel(int(channel_id))
            return channel
        except discord.errors.NotFound:
            logger.error(f"🔴 Channel {channel_id} not found - check permissions")
            return None
        except discord.errors.Forbidden:
            logger.error(f"🔴 No permission to access channel {channel_id}")
            return None
        except Exception as e:
            logger.error(f"🔴 Error fetching channel {channel_id}: {e}")
            return None

    async def send_message(self, channel_key, content):
        if not self.enabled: return
        
        channel = await self._get_channel(channel_key)
        if channel:
            try:
                await channel.send(content)
                self._last_successful_send = datetime.utcnow()
            except Exception as e:
                logger.error(f"🔴 Failed to send message: {e}")

    async def send_embed(self, channel_key, title, description, color=0x00ff00, fields=None):
        if not self.enabled: return
        
        channel = await self._get_channel(channel_key)
        if not channel: 
            logger.warning(f"🟡 Cannot send embed - channel '{channel_key}' not available")
            return

        # Use JST for display
        jst = datetime.utcnow() + timedelta(hours=9)
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
            # timestamp removed
        )
        embed.set_footer(text=f"Coffin299 Trader | {jst.strftime('%Y-%m-%d %H:%M:%S')} JST")
        
        if fields:
            for field in fields:
                embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', True))

        try:
            await channel.send(embed=embed)
            self._last_successful_send = datetime.utcnow()
        except discord.errors.HTTPException as e:
            logger.error(f"🔴 Discord HTTP error sending embed: {e.status} - {e.text}")
        except Exception as e:
            logger.error(f"🔴 Failed to send embed: {e}")

    async def notify_trade(self, action, pair, price, quantity, reason, pnl=None, currency="JPY", total_jpy=None):
        """
        Buffers trade alerts to be sent in batches.
        """
        if not self.enabled: return

        color = 0x00ff00 if action == "BUY" else 0xff0000
        
        # Use JST for display
        jst = datetime.utcnow() + timedelta(hours=9)
        
        embed = discord.Embed(
            title=f"{action} {pair}",
            description=f"**Price:** {price}\n**Qty:** {quantity}",
            color=color
            # timestamp removed to avoid confusion
        )
        
        if total_jpy:
             embed.add_field(name="Value (JPY)", value=f"¥{total_jpy:,.0f}", inline=True)
             
        embed.add_field(name="Reason", value=reason, inline=False)
        
        if pnl:
             embed.add_field(name="PnL", value=f"{pnl} {currency}", inline=True)

        embed.set_footer(text=f"Coffin299 Trader | {jst.strftime('%Y-%m-%d %H:%M:%S')} JST")
        
        # Add to buffer
        self.notification_buffer.append(embed)

    async def notify_balance(self, total_balance, currency="JPY", changes=None, total_pnl_usd=None, total_pnl_jpy=None):
        """
        Sends wallet updates to the 'wallet_updates' channel.
        """
        fields = []
        if changes:
            for coin, amount in changes.items():
                fields.append({"name": coin, "value": f"{amount}", "inline": True})
        
        description = f"Total Balance: **{total_balance:,.2f} {currency}**"
        
        if total_pnl_usd is not None and total_pnl_jpy is not None:
            pnl_color = "🟢" if total_pnl_usd >= 0 else "🔴"
            description += f"\nTotal PnL: {pnl_color} **${total_pnl_usd:,.2f}** (¥{total_pnl_jpy:,.0f})"
            
        await self.send_embed(
            channel_key='wallet_updates',
            title="💰 Wallet Update",
            description=description,
            color=0x3498db,
            fields=fields
        )

    async def notify_learning_status(self, message, pair, accuracy=None):
        """
        Sends AI learning status updates to the 'ai_learning' channel.
        """
        fields = [{"name": "Target Pair", "value": pair, "inline": True}]
        if accuracy:
            fields.append({"name": "Model Accuracy", "value": f"{accuracy:.2%}", "inline": True})
            
        await self.send_embed(
            channel_key='ai_learning',
            title="🧠 AI Learning Update",
            description=message,
            color=0x9b59b6, # Purple
            fields=fields
        )
