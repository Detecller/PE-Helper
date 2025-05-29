import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import logging
from utils.setup_logger import setup_logging


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize logging before anything else
setup_logging()

# Get logger
logger = logging.getLogger("pe_helper")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    guild = discord.utils.get(bot.guilds, name="NYP Piano Ensemble")
    if guild:
        await bot.tree.sync(guild=guild)
        logger.info(f"Slash commands synced to: {guild.name}")


async def main(): 
    await bot.load_extension("cogs")
    await bot.start(TOKEN)


asyncio.run(main())