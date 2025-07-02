import discord
from discord.ext import commands
from discord import app_commands

TEST_GUILD_ID = 1389129242423332884

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check if the bot is alive")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏓 Pong!", ephemeral=True)

# ✅ This is the missing function!
async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))

