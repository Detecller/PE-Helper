import discord
from discord.ext import commands
from discord import app_commands, Object
from discord.ui import Select, View
from utils.permissions import has_allowed_role_and_channel
import os
from utils.setup_logger import log_slash_command
import logging


GUILD_ID = int(os.getenv("GUILD_ID"))

# Get logger
logger = logging.getLogger("pe_helper")


class Members(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    members_group = app_commands.Group(name="members", description="Member-related commands")


    @members_group.command(name="list-current-exco", description="Lists names of those in the current EXCO.")
    @has_allowed_role_and_channel(allowed_channels=['💬┃general-commands', '🚧┃test-commands'])
    async def list_current_exco(self, interaction: discord.Interaction):

        await interaction.response.defer()

        log_slash_command(logger, interaction)

        guild = interaction.guild
        exco = sorted([m.display_name for m in guild.members if any(r.name=="Current EXCO" for r in m.roles)], key=str.lower)
        
        if not exco:
            logger.warning("No current EXCO members found.")
            await interaction.response.send_message("No current EXCO members found.")
            return
        
        logger.info(f"Found {len(exco)} EXCO members.")
        text = "**Names of Current EXCO Members:**\n" + "\n".join(f"- {n}" for n in exco)
        await interaction.followup.send(text)

    
    @members_group.command(name="list-piano-group-members", description="Select a piano group and list its members (excl. alumni).")
    @has_allowed_role_and_channel(allowed_channels=['💬┃general-commands', '🚧┃test-commands'])
    async def list_piano_group_members(self, interaction: discord.Interaction):

        await interaction.response.defer()

        log_slash_command(logger, interaction)

        class Dropdown(Select):
            def __init__(self):

                # Create dropdown options for each piano group
                opts = [discord.SelectOption(label=g) for g in ["Foundational","Novice","Intermediate","Advanced"]]
                super().__init__(placeholder="Choose a group…", min_values=1, max_values=1, options=opts)


            async def callback(self, inter: discord.Interaction):
                grp = self.values[0]
                logger.info(f"Piano group selected: {grp} by {inter.user.display_name}")

                # Get list of members from the selected group (excluding alumni)
                names = [m.display_name for m in inter.guild.members if grp in {r.name for r in m.roles} and "Member" in {r.name for r in m.roles}]
                
                # If there are members in the group, sort and display their names
                if names:
                    names.sort(key=str.lower)
                    out = "\n".join(f"- {n}" for n in names)
                    logger.info(f"Listed {len(names)} members in group {grp}.")
                    await inter.response.send_message(f"**{grp} members:**\n{out}", ephemeral=True)
                else:
                    logger.warning(f"No current members found in group {grp}.")
                    await inter.response.send_message(f"No current members in {grp}.", ephemeral=True)


        # Create a view for the select dropdown
        view = View()
        view.add_item(Dropdown())
        
        logger.info("Dropdown sent for piano group selection.")
        await interaction.followup.send("Please select a group:", view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Members(bot), guild=Object(id=GUILD_ID))