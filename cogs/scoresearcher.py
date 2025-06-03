import discord
from discord.ext import commands
from discord import app_commands
from utils.permissions import has_allowed_role_and_channel
import pandas as pd
from utils.web_searching import search_scores

composers = ["Chopin", "J.S Bach", "Beethoven", "Mozart", "Liszt", "Rachmaninoff", "Debussy", "R.Schumann", "C.Schumann",
             "Schubert", "Tchaikovsky", "Czerny", "Haydn", "Mendelssohn", "Moszkowski", "Ravel", "Erik Satie", "Scarlatti"]

file_path = r"C:\Users\yanya\PycharmProjects\PE-Helper\cogs\composers.csv"


try:
    df = pd.read_csv(file_path)
except FileNotFoundError:
    data = {"Composers": composers, "Searches": [0 for _ in range(len(composers))]}
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)

def update_composers(composer, increment=1):
    df = pd.read_csv(file_path)
    new_quantity = int(df.loc[df['Composers'] == composer, "Searches"]) + increment
    df.loc[df['Composers'] == composer, "Searches"] = new_quantity
    df.to_csv(file_path, index=False)


async def classical_composers_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    df = pd.read_csv(file_path)
    final_df = df.sort_values(by="Searches", ascending=False)
    valid_composers = list(final_df['Composers'])
    if current:
        return [i for i in valid_composers if current.lower() in i.lower()]
    return [i for i in valid_composers]

class ScoreSearcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="search_piece", description="Search for classical pieces!")
    @has_allowed_role_and_channel()
    @app_commands.autocomplete(composer=classical_composers_autocomplete)
    async def search_piece(self, interaction: discord.Interaction, piece: str, composer: str):
        update_composers(composer)
        search_term = f"{piece} - {composer}"
        results = search_scores(search_term)
        scores = results['imslp_scores']
        formatted_scores = [f"[{i['name']}]({i['link']})\nScore: {i['points']}" for i in scores]
        embed = discord.Embed(title=f"Results from ({results['title']})\n{results['link']}", description='\n'.join(formatted_scores))
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.bot):
    await bot.add_cog(ScoreSearcher(bot))