import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import logging
from utils.setup_logger import setup_logging

import aiosqlite

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
APP_ID = int(os.getenv("APPLICATION_ID"))

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True

class MyBot(commands.Bot):
    async def setup_hook(self):
        extensions = ["cogs.members", "cogs.stats", "cogs.background_tasks"]
        
        for extension in extensions:
            try:
                await bot.load_extension(extension)
                logger.info(f"Loaded: {extension}")

            except Exception as e:
                logger.error(f"Failed to load {extension}: {e}")
                import traceback
                logger.error(traceback.format_exc())


bot = MyBot(command_prefix="!", intents=intents, application_id=APP_ID)

# Initialize logging before anything else
setup_logging()

# Get logger
logger = logging.getLogger("pe_helper")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    guild = discord.utils.get(bot.guilds, name="NYP Piano Ensemble")
    if guild:
        try:
            # Sync commands
            logger.info("Syncing commands...")
            synced = await bot.tree.sync(guild=discord.Object(id=guild.id))
            logger.info(f"Synced {len(synced)} guild commands: {[cmd.name for cmd in synced]}")
            con = await aiosqlite.connect("PEHelper.db")
            scoresearcher.con = con
            
        except Exception as e:
            logger.error(f"Error in on_ready: {e}")
            import traceback
            logger.error(traceback.format_exc())


bot.run(TOKEN)