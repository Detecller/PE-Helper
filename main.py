import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    guild = discord.utils.get(bot.guilds, name="NYP Piano Ensemble")
    if guild:
        await bot.tree.sync(guild=guild)
        print(f"Slash commands synced to: {guild.name}")


async def main():
    await bot.load_extension("cogs")
    await bot.start(TOKEN)


asyncio.run(main())