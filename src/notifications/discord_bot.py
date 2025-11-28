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
        if self.enabled and self.token:
            intents = discord.Intents.default()
            self.client = discord.Client(intents=intents)
            
            @self.client.event
            async def on_ready():
                logger.info(f"Discord Bot logged in as {self.client.user}")

    async def start(self):
        """
        Starts the Discord client in the background.
        """
        if self.client and self.token:
            try:
                # Start the client without blocking
                asyncio.create_task(self.client.start(self.token))
            except Exception as e:
                logger.error(f"Failed to start Discord bot: {e}")

    async def _get_channel(self, channel_key):
        if not self.client or not self.client.is_ready():
            logger.warning("Discord client not ready.")
            return None
            
        channel_id = self.channels.get(channel_key)
        if not channel_id:
            logger.error(f"Channel ID for '{channel_key}' not configured.")
            return None
            
        try:
            channel = self.client.get_channel(int(channel_id))
            if not channel:
                channel = await self.client.fetch_channel(int(channel_id))
            return channel
        except Exception as e:
            logger.error(f"Error fetching channel {channel_id}: {e}")
            return None

    async def send_message(self, channel_key, content):
        if not self.enabled: return
        
        channel = await self._get_channel(channel_key)
        if channel:
            await channel.send(content)

    async def send_embed(self, channel_key, title, description, color=0x00ff00, fields=None):
        if not self.enabled: return
        
        channel = await self._get_channel(channel_key)
        if not channel: return

        # Use JST for display
        jst = datetime.utcnow() + timedelta(hours=9)
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow() # Discord uses this to show "Today at X:XX PM" in user's local time
        )
        embed.set_footer(text=f"Coffin299 Trader | {jst.strftime('%Y-%m-%d %H:%M:%S')} JST")
        
        if fields:
            for field in fields:
                embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', True))

        try:
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send embed: {e}")

    async def notify_trade(self, action, pair, price, quantity, reason, pnl=None, currency="JPY", total_jpy=None):
        """
        Sends trade alerts to the 'trade_alerts' channel.
        """
        color = 0x00ff00 if action == "BUY" else 0xff0000
        fields = [
            {"name": "Pair", "value": pair, "inline": True},
            {"name": "Price", "value": f"{price}", "inline": True},
            {"name": "Quantity", "value": f"{quantity}", "inline": True},
        ]
        
        if total_jpy:
             fields.append({"name": "Total Value (JPY)", "value": f"¥{total_jpy:,.0f}", "inline": True})
             
        fields.append({"name": "Reason", "value": reason, "inline": False})
        
        if pnl:
             fields.append({"name": "PnL", "value": f"{pnl} {currency}", "inline": True})

        await self.send_embed(
            channel_key='trade_alerts',
            title=f"🚀 Trade Executed: {action}",
            description=f"Successfully executed {action} order.",
            color=color,
            fields=fields
        )

    async def notify_balance(self, total_balance, currency="JPY", changes=None):
        """
        Sends wallet updates to the 'wallet_updates' channel.
        """
        fields = []
        if changes:
            for coin, amount in changes.items():
                fields.append({"name": coin, "value": f"{amount}", "inline": True})
        
        await self.send_embed(
            channel_key='wallet_updates',
            title="💰 Wallet Update",
            description=f"Total Balance: **{total_balance:,.2f} {currency}**",
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
