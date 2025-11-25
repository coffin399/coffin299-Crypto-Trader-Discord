import aiohttp
import json
from datetime import datetime
from ..logger import setup_logger

logger = setup_logger("discord_bot")

class DiscordNotifier:
    def __init__(self, webhook_url, enabled=True):
        self.webhook_url = webhook_url
        self.enabled = enabled

    async def send_message(self, content):
        if not self.enabled or not self.webhook_url:
            return

        payload = {"content": content}
        await self._post(payload)

    async def send_embed(self, title, description, color=0x00ff00, fields=None):
        if not self.enabled or not self.webhook_url:
            return

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "Coffin299 Trader"}
        }
        
        if fields:
            embed["fields"] = fields

        payload = {"embeds": [embed]}
        await self._post(payload)

    async def _post(self, payload):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status not in [200, 204]:
                        logger.error(f"Failed to send Discord notification: {response.status} {await response.text()}")
        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")

    async def notify_trade(self, action, pair, price, quantity, reason, pnl=None, currency="JPY"):
        """
        Sends a rich embed for trade execution.
        """
        color = 0x00ff00 if action == "BUY" else 0xff0000
        fields = [
            {"name": "Pair", "value": pair, "inline": True},
            {"name": "Price", "value": f"{price}", "inline": True},
            {"name": "Quantity", "value": f"{quantity}", "inline": True},
            {"name": "Reason", "value": reason, "inline": False}
        ]
        
        if pnl:
             fields.append({"name": "PnL", "value": f"{pnl} {currency}", "inline": True})

        await self.send_embed(
            title=f"🚀 Trade Executed: {action}",
            description=f"Successfully executed {action} order.",
            color=color,
            fields=fields
        )

    async def notify_balance(self, total_balance, currency="JPY", changes=None):
        """
        Sends hourly balance update.
        """
        fields = []
        if changes:
            for coin, amount in changes.items():
                fields.append({"name": coin, "value": f"{amount}", "inline": True})
        
        await self.send_embed(
            title="💰 Wallet Update",
            description=f"Total Balance: **{total_balance:,.2f} {currency}**",
            color=0x3498db,
            fields=fields
        )
