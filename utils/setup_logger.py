import logging
from logging.handlers import RotatingFileHandler
import discord


def create_rotating_handler(filename, level=logging.INFO, max_bytes=1_000_000, backups=5):
    handler = RotatingFileHandler(filename, maxBytes=max_bytes, backupCount=backups, encoding="utf-8")
    handler.setLevel(level)

    class CategoryFormatter(logging.Formatter):
        def format(self, record):
            cat = getattr(record, "category", None)
            if cat:
                if isinstance(cat, list):
                    cat = ",".join(cat)
                # Avoid double brackets if already present
                if not (cat.startswith("[") and cat.endswith("]")):
                    cat = f"[{cat}]"
            else:
                cat = ""
            record.category = cat
            return super().format(record)

    
    formatter = CategoryFormatter("%(asctime)s - %(levelname)s - %(category)s %(message)s")
    handler.setFormatter(formatter)
    return handler


# Initialise logger
def setup_logging():
    # Bot logger
    bot_logger = logging.getLogger("pe_helper")
    bot_logger.setLevel(logging.INFO)
    bot_logger.addHandler(create_rotating_handler("../logs/pe_helper.log"))
    bot_logger.addHandler(create_rotating_handler("../logs/pe_helper_errors.log", level=logging.ERROR))
    bot_logger.addHandler(logging.StreamHandler())

    # Discord logger
    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.INFO)
    discord_logger.addHandler(create_rotating_handler("../logs/discord.log"))
    discord_logger.addHandler(create_rotating_handler("../logs/discord_errors.log", level=logging.ERROR))


# Log name of user using command, along with the channel in which command is used
def log_slash_command(logger, interaction: discord.Interaction):
    command_name = interaction.command.name if interaction.command else "unknown"
    user = interaction.user
    channel = interaction.channel
    logger.info(
        f"/{command_name} used by {user.display_name} (ID: {user.id}) in #{channel}",
        extra={"category": "command_usage"}
    )