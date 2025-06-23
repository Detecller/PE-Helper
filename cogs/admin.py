import discord
from discord.ext import commands
from discord import app_commands, Object, ui, ButtonStyle
import logging
import sys
import os
import time
from utils.variables import START_TIME
import psutil
import platform
from utils.permissions import has_allowed_role_and_channel


GUILD_ID = int(os.getenv("GUILD_ID"))

# Get logger
logger = logging.getLogger("pe_helper")


class ConfirmView(ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.value = None  # Store user choice

    @ui.button(label="Confirm", style=ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.value = True
        self.stop()
        await interaction.response.edit_message(content="Confirmed. Shutting down...", view=None)

    @ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.value = False
        self.stop()
        await interaction.response.edit_message(content="Shutdown cancelled.", view=None)


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    
    admin_group = app_commands.Group(name="admin", description="Admin commands")


    @admin_group.command(name="shutdown", description="Gracefully shuts down the bot.")
    @has_allowed_role_and_channel(allowed_roles=['Admin'], allowed_channels=['⚙️┃admin-related'])
    async def shutdown(self, interaction: discord.Interaction):
        view = ConfirmView()
        await interaction.response.send_message("Are you sure you want to shut down the bot?", view=view)
        
        # Wait for user to respond or timeout
        await view.wait()

        if view.value is True:
            await self.bot.close()
        elif view.value is False:
            pass
        else:
            await interaction.followup.send("No response, shutdown cancelled.")


    @admin_group.command(name="restart", description="Restarts the bot.")
    @has_allowed_role_and_channel(allowed_roles=['Admin'], allowed_channels=['⚙️┃admin-related'])
    async def restart(self, interaction: discord.Interaction):
        await interaction.response.send_message("PE Helper has been restarted.")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    

    @admin_group.command(name="reload", description="Reloads a cog/module.")
    @has_allowed_role_and_channel(allowed_roles=['Admin'], allowed_channels=['⚙️┃admin-related'])
    @app_commands.describe(cog="Name of the cog/module to reload. Use 'all' to reload everything.")
    async def reload(self, interaction: discord.Interaction, cog: str):
        try:
            if cog == "all":
                for ext in list(self.bot.extensions):
                    await self.bot.reload_extension(ext)
                logger.info(f"Reloaded all cogs.")
                await interaction.response.send_message("Reloaded all cogs.")
            else:
                await self.bot.reload_extension(f"cogs.{cog}")
                logger.info(f"Reloaded cogs.{cog}.")
                await interaction.response.send_message(f"Reloaded `cogs.{cog}`.")
        except Exception as e:
            logger.warning(f"Reload failed: {e}")
            await interaction.response.send_message(f"Reload failed: {e}", ephemeral=True)
    

    @admin_group.command(name="info", description="Bot stats like uptime, memory, CPU.")
    @has_allowed_role_and_channel(allowed_roles=['Admin'], allowed_channels=['⚙️┃admin-related'])
    async def info(self, interaction: discord.Interaction):

        uptime = time.time() - START_TIME
        mem = psutil.Process().memory_info().rss / (1024 ** 2)
        cpu = psutil.cpu_percent(interval=0.5)

        embed = discord.Embed(title="Bot Info")
        embed.add_field(name="Uptime", value=f"{int(uptime // 60)} min", inline=True)
        embed.add_field(name="Memory", value=f"{mem:.2f} MB", inline=True)
        embed.add_field(name="CPU", value=f"{cpu}%", inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot), guild=Object(id=GUILD_ID))