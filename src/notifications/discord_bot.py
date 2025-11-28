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
        
        self.notification_buffer = []

    async def start(self):
        """
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
