import discord
import datetime

class DiscordEmbedGenerator:
    @staticmethod
    def create_trade_embed(side, symbol, price, quantity, value_jpy, strategy_name):
        color = discord.Color.green() if side.upper() == 'BUY' else discord.Color.red()
        
        embed = discord.Embed(
            title=f"🚀 {side.upper()} {symbol}",
            color=color,
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="Price", value=f"{price:.8f}", inline=True)
        embed.add_field(name="Value (JPY)", value=f"¥{value_jpy:,.0f}", inline=True)
        embed.add_field(name="Quantity", value=f"{quantity:.4f}", inline=True)
        embed.add_field(name="Strategy", value=strategy_name, inline=True)
        embed.set_footer(text="Binance Trader")
        
        return embed

    @staticmethod
    def create_wallet_summary_embed(total_value_jpy, change_1h_jpy, total_change_jpy, title="💼 Wallet Summary"):
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="Total Value", value=f"¥{total_value_jpy:,.0f}", inline=False)
        embed.add_field(name="1H Change", value=f"¥{change_1h_jpy:,.0f}", inline=True)
        embed.add_field(name="Total Change", value=f"¥{total_change_jpy:,.0f}", inline=True)
        embed.set_footer(text="Binance Trader")
        
        return embed
