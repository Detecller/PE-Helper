import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from utils.discord_handler import DiscordHandler
from utils.setup_logger import setup_logging
import traceback


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
APP_ID = int(os.getenv("APPLICATION_ID"))
MUSIC_CHANNEL_ID = int(os.getenv("MUSIC_CHANNEL_ID"))

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True

class PEHelper(commands.Bot):
    async def setup_hook(self):
        extensions = [
            "cogs.admin",
            "cogs.members",
            "cogs.stats",
            "cogs.background_tasks",
            "cogs.score_searcher",
            "cogs.sheet_retriever",
            "cogs.music_bot",
            "cogs.exco_exclusive"
        ]
        
        for extension in extensions:
            try:
                await bot.load_extension(extension)
                logger.info(f"Loaded: {extension}")

            except Exception as e:
                logger.error(f"Failed to load {extension}: {e}")
                logger.error(traceback.format_exc())


bot = PEHelper(command_prefix="!", intents=intents, application_id=APP_ID)

# Initialize logging before anything else
setup_logging()

# Get logger
logger = logging.getLogger("pe_helper")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}", extra={"category": "on_ready"})
    guild = discord.utils.get(bot.guilds, name="NYP Piano Ensemble")
    if guild:
        try:
            try:
                audio_folder = "audios"
                if os.path.exists(audio_folder):
                    for file in os.listdir(audio_folder):
                        file_path = os.path.join(audio_folder, file)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    logger.info("Cleaned up leftover audio files on startup.", extra={"category": "on_ready"})
            except Exception as e:
                logger.warning(f"Error cleaning up audio files on startup: {e}", extra={"category": "on_ready"})
                
            # Sync commands
            logger.info("Syncing commands...", extra={"category": "on_ready"})
            synced = await bot.tree.sync(guild=discord.Object(id=guild.id))
            logger.info(f"Synced {len(synced)} guild commands: {[cmd.name for cmd in synced]}", extra={"category": "on_ready"})

            music_channel = bot.get_channel(MUSIC_CHANNEL_ID)
            if music_channel and isinstance(music_channel, discord.VoiceChannel):
                await music_channel.connect()
                logger.info(f"Joined voice channel: {music_channel.name}", extra={"category": "on_ready"})
            else:
                logger.warning("Voice channel not found or invalid.", extra={"category": "on_ready"})

            # Add Discord error handler
            error_channel = discord.utils.get(guild.text_channels, name="❗┃error-logs")
            if error_channel:
                discord_handler = DiscordHandler(error_channel)
                discord_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
                logger.addHandler(discord_handler)
                logger.info("DiscordHandler attached.", extra={"category": "on_ready"})
            else:
                logger.warning("Could not find error log channel.", extra={"category": "on_ready"})
            
        except Exception as e:
            logger.error("Error in on_ready: %s\n%s", e, traceback.format_exc(), extra={"category": "on_ready"})


@bot.event
async def on_message(message):
    # Ignore bot messages
    if message.author.bot:
        return

    # Specify category to apply message deletion
    target_category_name = "Commands"

    category = message.channel.category
    if category and category.name == target_category_name:
        await message.delete()
        logger.warning(
            f"Deleted message from {message.author.display_name} (ID: {message.author.id}) in #{message.channel} (Category: {category.name}): {message.content}",
            extra={"category": ["on_message", "message_deletion"]}
        )
        return


bot.run(TOKEN)