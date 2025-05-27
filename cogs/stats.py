import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.permissions import has_allowed_role_and_channel
from utils.variables import SGT, last_update
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
import datetime


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    #     self.count_messages_task = None


    # @commands.Cog.listener()
    # async def on_ready(self):
    #     if self.count_messages_task is None or not self.count_messages_task.is_running():
    #         print("Starting count_messages loop...")
    #         self.count_messages_task = self.count_messages.start()
    #     else:
    #         print("count_messages task already running.")


    # @tasks.loop(hours=1)
    # async def count_messages(self):
    #     guild = discord.utils.get(self.bot.guilds, name="NYP Piano Ensemble")
    #     message_counts: dict[str, int] = {}
    #     word_counts: dict[str, int] = {}
    #     target_roles = ['Member', 'Alumni']
    #     role_objs = [discord.utils.get(guild.roles, name=r) for r in target_roles]

    #     scanned = []
    #     for ch in guild.text_channels:
    #         if not any(ch.permissions_for(role).view_channel for role in role_objs if role):
    #             continue
    #         try:
    #             async for msg in ch.history(limit=None):
    #                 if not isinstance(msg.author, discord.Member) or msg.author.bot:
    #                     continue
    #                 name = msg.author.display_name
    #                 message_counts.setdefault(name, 0)
    #                 word_counts.setdefault(name, 0)
    #                 message_counts[name] += 1
    #                 word_counts[name] += len(msg.content.split())
    #         except discord.Forbidden:
    #             continue
    #         scanned.append(ch.name)

    #     df = pd.DataFrame([
    #         {"Name": n, "Message Count": message_counts[n], "Word Count": word_counts[n]}
    #         for n in message_counts
    #     ])
        
    #     df.sort_values("Message Count", ascending=False).head(10).to_csv("data/top_messages.csv", index=False)
    #     df.sort_values("Word Count", ascending=False).head(10).to_csv("data/top_words.csv", index=False)
    #     with open("data/channels.txt", "w", encoding="utf-8") as f:
    #         f.write("\n".join(scanned))
    #     global last_update
    #     last_update = datetime.datetime.now(SGT)

    
    @app_commands.command(name="piano_groups", description="Pie chart of piano-playing groups of current members.")
    @has_allowed_role_and_channel()
    async def piano_groups(self, interaction: discord.Interaction):
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

        await interaction.response.send_message(file=discord.File(buf, "piano_groups.png"))


    @app_commands.command(name="message_stats", description="Bar charts of total messages & word counts by user.")
    @has_allowed_role_and_channel(forbidden_roles=['Member','Alumni'], forbidden_channels=['💬┃general'])
    async def message_stats(self, interaction: discord.Interaction):
        with open("data/channels.txt", "r", encoding="utf-8") as f:
            channels = f.read().splitlines()
        
        df_msg = pd.read_csv("data/top_messages.csv")
        df_words = pd.read_csv("data/top_words.csv")

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
        await interaction.response.send_message(header)
        await interaction.followup.send(file=discord.File(buf1, "message_count.png"))
        await interaction.followup.send(file=discord.File(buf2, "word_count.png"))
        await interaction.followup.send(f"Last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')} SGT")


async def setup(bot: commands.bot):
    await bot.add_cog(Stats(bot))