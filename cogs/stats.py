import discord
from discord.ext import commands
from discord import app_commands, Object
from utils.permissions import has_allowed_role_and_channel
from utils.variables import last_update
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
from utils.setup_logger import log_slash_command
import logging
from datetime import datetime
from utils.variables import SGT
import os
import traceback


GUILD_ID = int(os.getenv("GUILD_ID"))

# Get logger
logger = logging.getLogger("pe_helper")


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    stats_group = app_commands.Group(name="stats", description="Statistical commands")


    @stats_group.command(name="piano-groups", description="Pie chart of piano-playing groups of current members.")
    @has_allowed_role_and_channel(allowed_channels=['💬┃general-commands', '🚧┃test-commands'])
    async def piano_groups(self, interaction: discord.Interaction):

        await interaction.response.defer()

        log_slash_command(logger, interaction)

        guild = interaction.guild
        count_dict = {"Advanced": 0, "Intermediate": 0, "Novice": 0, "Foundational": 0}

        for m in guild.members:
            if m.bot:
                continue
            roles = {r.name for r in m.roles}
            if "Member" in roles:  # Obtain current members only
                if "Advanced" in roles:
                    count_dict["Advanced"] += 1
                elif "Intermediate" in roles:
                    count_dict["Intermediate"] += 1
                elif "Novice" in roles:
                    count_dict["Novice"] += 1
                elif "Foundational" in roles:
                    count_dict["Foundational"] += 1

        logger.info(f"Counting of members in piano groups was successful.", extra={"category": ["stats", "piano_groups"]})

        # Generate pie chart for roles
        labels = ["Foundational", "Novice", "Intermediate", "Advanced"]
        values = [count_dict[label] for label in labels]

        label_colors = {
            "Advanced": "#05668d",
            "Intermediate": "#427aa1",
            "Novice": "#679436",
            "Foundational": "#a5be00"
        }

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=[label_colors[label] for label in labels]),
            textinfo='value+percent',
            sort=False
        )])
        fig.update_layout(
            title="Piano-Playing Groups of Current Members",
            legend=dict(traceorder="normal")
        )

        # Save the figure to an image in memory
        buf = BytesIO()
        fig.write_image(buf, format="png")
        buf.seek(0)

        try:
            await interaction.followup.send(file=discord.File(buf, "piano_groups.png"))
            logger.info("Piano groups pie chart sent successfully.", extra={"category": ["stats", "piano_groups"]})
        except Exception as e:
            logger.error(f"Failed to send piano groups pie chart: %s\n%s", e, traceback.format_exc(), extra={"category": ["sheet_retriever", "view_pe_sheets"]})


    @stats_group.command(name="message-stats", description="Bar charts of total messages & word counts by user.")
    @has_allowed_role_and_channel(allowed_channels=['💬┃general-commands', '🚧┃test-commands'])
    async def message_stats(self, interaction: discord.Interaction):

        await interaction.response.defer()

        log_slash_command(logger, interaction)

        try:
            with open("../data/channels.txt", "r", encoding="utf-8") as f:
                channels = f.read().splitlines()
            logger.info(f"Loaded {len(channels)} channels from file.", extra={"category": ["stats", "message_stats"]})
        except Exception as e:
            logger.error(f"Failed to read channels.txt: %s\n%s", e, traceback.format_exc(), extra={"category": ["stats", "message_stats"]})
            await interaction.response.send_message("Error reading channels data.", ephemeral=True)
            return
        
        try:
            df_msg = pd.read_csv("../data/top_messages.csv")
            df_words = pd.read_csv("../data/top_words.csv")
            logger.info(f"Loaded message and word count CSV files.", extra={"category": ["stats", "message_stats"]})
        except Exception as e:
            logger.error(f"Failed to read CSV files: %s\n%s", e, traceback.format_exc(), extra={"category": ["stats", "message_stats"]})
            await interaction.response.send_message("Error reading stats data.", ephemeral=True)
            return

        # Create a horizontal bar chart of message counts
        fig1 = go.Figure(data=go.Bar(
            x=df_msg["Message Count"],
            y=df_msg["Name"],
            orientation='h',
            text=df_msg["Message Count"],
            marker=dict(color='#1985a1')
        ))
        fig1.update_layout(
            title='Top 10 Message Senders',
            xaxis_title='Total Messages',
            yaxis_title='Name',
            yaxis=dict(autorange='reversed', ticksuffix='  '),
            plot_bgcolor='white',
            title_x=0.5
        )
        buf1 = BytesIO()
        fig1.write_image(buf1, format="png")
        buf1.seek(0)

        # Create a horizontal bar chart of word counts
        fig2 = go.Figure(data=go.Bar(
            x=df_words["Word Count"],
            y=df_words["Name"],
            orientation='h',
            text=df_words["Word Count"],
            marker=dict(color='#284b63')
        ))
        fig2.update_layout(
            title='Top 10 Users by Word Count',
            xaxis_title='Total Words',
            yaxis_title='Name',
            yaxis=dict(autorange='reversed', ticksuffix='  '),
            plot_bgcolor='white',
            title_x=0.5
        )
        buf2 = BytesIO()
        fig2.write_image(buf2, format="png")
        buf2.seek(0)

        # Send channel list header and the images
        header = "**Scanned Channels:**\n" + "\n".join(f"- {c}" for c in channels)
        try:
            await interaction.followup.send(header)
            await interaction.followup.send(file=discord.File(buf1, "message_count.png"))
            await interaction.followup.send(file=discord.File(buf2, "word_count.png"))
            await interaction.followup.send(f"Last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')} SGT")
            logger.info("Sent message stats charts and last updated info.", extra={"category": ["stats", "message_stats"]})
        except Exception as e:
            logger.error(f"Failed to send message stats charts: %s\n%s", e, traceback.format_exc(), extra={"category": ["stats", "message_stats"]})
    

    @stats_group.command(name="weekly-session-popularity", description="Line chart showing the trends in room registrations for the current academic year.")
    @has_allowed_role_and_channel(allowed_channels=['💬┃general-commands', '🚧┃test-commands'])
    async def weekly_session_popularity(self, interaction: discord.Interaction):

        await interaction.response.defer()

        log_slash_command(logger, interaction)

        df_sessions = pd.read_csv('../data/all_bookings.csv')

        today = datetime.now(SGT).date()
        current_ay = today.year if today.month >= 4 else today.year - 1
        df_sessions = df_sessions[df_sessions['AY'] == current_ay]

        df_sessions['date'] = pd.to_datetime(df_sessions['date'])
        grouped = df_sessions.groupby(['date', 'room']).size().reset_index(name='registrants')
        pivot_df = grouped.pivot(index='date', columns='room', values='registrants').fillna(0)

        label_colors = {
            "PR9": "#102542",
            "PR10": "#1f7a8c"
        }

        # Create line chart
        fig = go.Figure()

        for room in pivot_df.columns:
            fig.add_trace(go.Scatter(
                x=pivot_df.index,
                y=pivot_df[room],
                mode='lines+markers',
                name=str(room),
                line=dict(color=label_colors.get(room))
            ))

        fig.update_layout(
            title=f"Trends in Room Registrations for AY{current_ay}",
            xaxis_title="Month",
            yaxis_title="Number of Registrants",
            plot_bgcolor='white',
            title_x=0.5,
            xaxis=dict(
                tickformat="%b",
                dtick="M1",
                showgrid=True,
                gridcolor="lightgray",
                griddash="dash",
                ticklabelmode="period",
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="lightgray",
                griddash="dot",
                rangemode="tozero"
            )
        )

        buf = BytesIO()
        fig.write_image(buf, format="png")
        buf.seek(0)

        await interaction.followup.send(file=discord.File(buf, "weekly_session_trend.png"))
        await interaction.followup.send("Note: Updates daily at 5 PM SGT.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot), guild=Object(id=GUILD_ID))