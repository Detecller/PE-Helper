import discord
from discord.ext import commands
from discord import app_commands, Object
from utils.permissions import has_allowed_role_and_channel
import pandas as pd
from utils.web_searching import search_scores
from utils.setup_logger import log_slash_command
import os
import logging


GUILD_ID = int(os.getenv("GUILD_ID"))

composers = ["Chopin", "J.S Bach", "Beethoven", "Mozart", "Liszt", "Rachmaninoff", "Debussy", "R.Schumann", "C.Schumann",
             "Schubert", "Tchaikovsky", "Czerny", "Haydn", "Mendelssohn", "Moszkowski", "Ravel", "Erik Satie", "Scarlatti"]

file_path = "data/composers.csv"
logger = logging.getLogger("pe_helper")


try:
    df = pd.read_csv(file_path)
except FileNotFoundError:
    data = {"Composers": composers, "Searches": [0 for _ in range(len(composers))]}
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)


def update_composers(composer, increment=1):
    df = pd.read_csv(file_path)
    current_searches = df.loc[df['Composers'] == composer, "Searches"]
    if not current_searches.empty:
        new_quantity = int(current_searches.iloc[0]) + increment
        df.loc[df['Composers'] == composer, "Searches"] = new_quantity
        df.to_csv(file_path, index=False)


async def classical_composers_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    df = pd.read_csv(file_path)
    final_df = df.sort_values(by="Searches", ascending=False)
    valid_composers = list(final_df['Composers'])

    filtered = [i for i in valid_composers if current.lower() in i.lower()] if current else valid_composers
    return [app_commands.Choice(name=c, value=c) for c in filtered[:25]]


class ScoreSearcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    score_searcher_group = app_commands.Group(name="score-searcher", description="Score-searching commands")


    @score_searcher_group.command(name="search-piece", description="Search for classical pieces!")
    @has_allowed_role_and_channel(allowed_channels=['📖┃music-sheets', '🚧┃test-commands'])
    @app_commands.autocomplete(composer=classical_composers_autocomplete)
    async def search_piece(self, interaction: discord.Interaction, piece: str, composer: str):

        await interaction.response.defer()

        log_slash_command(logger, interaction)

        try:
            update_composers(composer)
            search_term = f"{piece} - {composer}"
            results = search_scores(search_term, interaction)
            scores = results['imslp_scores']
            formatted_scores = [f"[{i['name']}]({i['link']})\nNumber of Downloads: {i['points']}\n" for i in scores]
            embed = discord.Embed(
                title=f"Top 10 Results for {results['title']}",
                url=results['link'],
                description='\n'.join(formatted_scores)
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in /search_piece command: {e}", exc_info=True)
            await interaction.followup.send("❌ An unexpected error occurred.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ScoreSearcher(bot), guild=Object(id=GUILD_ID))