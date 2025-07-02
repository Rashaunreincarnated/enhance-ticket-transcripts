# main.py

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

TEST_GUILD_ID = 1389129242423332884
GUILD = discord.Object(id=TEST_GUILD_ID)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ Loaded cog: {filename}")
                except Exception as e:
                    print(f"❌ Failed to load cog {filename}: {e}")

        # ⚠️ Add this AFTER loading cogs to register persistent buttons
        from cogs.ticket import TicketActionView
        self.add_view(TicketActionView())

        try:
            await self.tree.sync(guild=GUILD)
            print(f"✅ Slash commands synced to test guild ({TEST_GUILD_ID}).")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_TOKEN not found in .env file")
