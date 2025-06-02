import discord
from discord.ext import commands
from discord import app_commands
from utils.permissions import has_allowed_role_and_channel
import numpy as np
import os
import pandas as pd
import aiosqlite
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from utils.web_searching import search_scores

composers = np.array(["Chopin", "J.S Bach", "Beethoven", "Mozart", "Liszt", "Rachmaninoff", "Debussy", "R.Schumann", "C.Schumann",
             "Schubert", "Tchaikovsky", "Czerny", "Haydn", "Mendelssohn", "Moszkowski", "Ravel", "Erik Satie", "Scarlatti"])
file_path = r"C:\Users\yanya\PycharmProjects\GitPEHelper\PE-Helper\cogs\test.csv"


try:
    df = pd.read_csv(file_path)
    print(f"{df.columns}\n{df.to_string()}")
except FileNotFoundError:
    data = {"Composers": composers, "Searches": [0 for _ in range(len(composers))]}
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)



async def classical_composers_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:

    if current:
        return [i for i in composers if current.lower() in i.lower()]
    return [i for i in composers]

class ScoreSearcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="search_piece", description="Search for classical pieces!")
    @has_allowed_role_and_channel()
    @app_commands.autocomplete(composer=classical_composers_autocomplete)
    async def search_piece(self, interaction: discord.Interaction, piece: str, composer: str):
        se