import discord
from discord.ext import commands
from discord.ui import Select, View
import pandas as pd
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter


load_dotenv()
token = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


# Check whether user has the authorised role and is in the correct channel
def restrict(forbidden_roles=None, forbidden_channels=None):
    if forbidden_roles is None:
        forbidden_roles = []
    if forbidden_channels is None:
        forbidden_channels = []
        
    def predicate(ctx):
        default_allowed_roles = ['Admin', 'Current EXCO', 'Member', 'Alumni']
        default_allowed_channels = ['🛠┃admin-discussions', '🧠┃exco-discussions', '💬┃general']

        # Remove forbidden roles and channels from allowed ones
        allowed_roles = [role for role in default_allowed_roles if role not in forbidden_roles]
        allowed_channels = [channel for channel in default_allowed_channels if channel not in forbidden_channels]

        user_roles = [role.name for role in ctx.author.roles]

        reasons = []

        # Check if the user has the required role
        if not any(role in allowed_roles for role in user_roles):
            reasons.append("❌ You don't have the permitted role to use this command.")
        
        # Check if the channel is not in the whitelist
        if ctx.channel.name not in allowed_channels:
            reasons.append("❌ This command cannot be used in this channel.")

        # If there are any failed checks, raise an exception
        if reasons:
            raise commands.CheckFailure("\n".join(reasons))

        return True

    return commands.check(predicate)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Connected to {len(bot.guilds)} server(s):")
    for guild in bot.guilds:
        print(f" - {guild.name}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(str(error))
    else:
        raise error


@bot.command()
@restrict()
async def piano_groups(ctx):
    """Shows a pie chart of piano-playing groups of current members in NYP PE."""
    
    guild = discord.utils.get(bot.guilds, name="NYP Piano Ensemble")
    count_dict = {"Advanced": 0, "Intermediate": 0, "Novice": 0, "Foundational": 0}

    for member in guild.members:
        if member.bot:
            continue
        role_names = [role.name for role in member.roles]

        if "Member" in role_names:  # Obtain current members only
            if "Advanced" in role_names:
                count_dict["Advanced"] += 1
            elif "Intermediate" in role_names:
                count_dict["Intermediate"] += 1
            elif "Novice" in role_names:
                count_dict["Novice"] += 1
            elif "Foundational" in role_names:
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
    img_bytes = BytesIO()
    fig.write_image(img_bytes, format='png')
    img_bytes.seek(0)

    await ctx.send("Here is the pie chart for piano-playing groups:", file=discord.File(img_bytes, 'piano_groups.png'))


@bot.command()
@restrict()
async def list_current_exco(ctx):
    """Lists the names of those in the current EXCO."""
    
    guild = discord.utils.get(bot.guilds, name="NYP Piano Ensemble")

    current_exco_list = []
    for member in guild.members:
            if any(role.name == 'Current EXCO' for role in member.roles):
                current_exco_list.append(member.display_name)

    current_exco_list = sorted(current_exco_list, key=lambda name: name.lower())
    current_exco_list_text = "**Here are the names of those in the current EXCO:**\n" + "\n".join(f"- {name}" for name in current_exco_list)
    await ctx.send(current_exco_list_text)


@bot.command()
@restrict()
async def list_piano_group_members(ctx):
    """Prompts for a piano-playing group and lists members with that role (excluding alumni)."""

    class PianoGroupDropdown(Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="Foundational"),
                discord.SelectOption(label="Novice"),
                discord.SelectOption(label="Intermediate"),
                discord.SelectOption(label="Advanced"),
            ]
            super().__init__(placeholder="Choose a piano group...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            selected_group = self.values[0]
            guild = interaction.guild

            members_in_group = []
            for member in guild.members:
                role_names = [role.name for role in member.roles]
                if selected_group in role_names and "Member" in role_names:
                    members_in_group.append(member.display_name)

            if members_in_group:
                members_in_group.sort()
                member_list = "\n".join(f"- {name}" for name in members_in_group)
                response = f"**Members in the {selected_group} group (excluding alumni):**\n{member_list}"
            else:
                response = f"No current members found in the {selected_group} group."

            await interaction.response.send_message(response, ephemeral=True)

    class PianoGroupView(View):
        def __init__(self):
            super().__init__()
            self.add_item(PianoGroupDropdown())

    await ctx.send("Please select a piano-playing group:", view=PianoGroupView())


@bot.command()
@restrict()
async def message_stats(ctx):
    """Shows 2 horizontal bar charts of total message and word counts respectively, in descending order, for both current members and alumni of NYP PE."""
    
    guild = discord.utils.get(bot.guilds, name="NYP Piano Ensemble")

    message_counts = {}
    word_counts = {}
    
    target_roles = ['Member', 'Alumni']
    role_objects = [discord.utils.get(guild.roles, name=role_name) for role_name in target_roles]

    scanned_channels = []
    for channel in guild.text_channels:
        if not any(channel.permissions_for(role).view_channel for role in role_objects if role):
            continue
        try:
            async for message in channel.history(limit=None):
                if message.author.bot:
                    continue

                name = message.author.display_name
                if name not in message_counts:
                    message_counts[name] = 0
                    word_counts[name] = 0

                message_counts[name] += 1
                word_counts[name] += len(message.content.split())

        except discord.Forbidden:
            print(f"Skipping inaccessible channel: {channel.name}")
        except discord.HTTPException as e:
            print(f"Error in {channel.name}: {e}")

        scanned_channels.append(channel.name)
    
    channel_list_text = "**Scanned Channels:**\n" + "\n".join(f"- {name}" for name in scanned_channels)
    await ctx.send(channel_list_text)

    df_messages = pd.DataFrame([
        {
            "Name": name,
            "Message Count": message_counts[name],
            "Word Count": word_counts[name]
        }
        for name in message_counts
    ])
    df_top_messages = df_messages.sort_values(by="Message Count", ascending=False, ignore_index=True).head(10)
    df_top_words = df_messages.sort_values(by="Word Count", ascending=False, ignore_index=True).head(10)

    # Create a horizontal bar chart of message counts
    fig_messages = go.Figure(data=go.Bar(
        x=df_top_messages["Message Count"],
        y=df_top_messages["Name"],
        orientation='h',
        text=df_top_messages["Message Count"],
        marker=dict(color='#1985a1')
    ))
    fig_messages.update_layout(
        title='Top 10 Message Senders',
        xaxis_title='Total Messages',
        yaxis_title='Name',
        yaxis=dict(
            autorange='reversed',
            ticksuffix='  '
        ),
        plot_bgcolor='white',
        title_x=0.5
    )

    # Create a horizontal bar chart of word counts
    fig_words = go.Figure(data=go.Bar(
        x=df_top_words["Word Count"],
        y=df_top_words["Name"],
        orientation='h',
        text=df_top_words["Word Count"],
        marker=dict(color='#284b63')
    ))
    fig_words.update_layout(
        title='Top 10 Users by Word Count',
        xaxis_title='Total Words',
        yaxis_title='Name',
        yaxis=dict(
            autorange='reversed',
            ticksuffix='  '
        ),
        plot_bgcolor='white',
        title_x=0.5
    )

    # Save the figures to images in memory
    img_bytes_1 = BytesIO()
    fig_messages.write_image(img_bytes_1, format='png')
    img_bytes_1.seek(0)

    img_bytes_2 = BytesIO()
    fig_words.write_image(img_bytes_2, format='png')
    img_bytes_2.seek(0)

    await ctx.send("Message Count Chart:", file=discord.File(img_bytes_1, 'message_count.png'))
    await ctx.send("Word Count Chart:", file=discord.File(img_bytes_2, 'word_count.png'))


@bot.command()
@restrict(forbidden_roles=['Member', 'Alumni'], forbidden_channels=['💬┃general'])
async def members_details(ctx):
    """Lists all available details relating to members and alumni in Excel format."""
    
    guild = discord.utils.get(bot.guilds, name="NYP Piano Ensemble")
    
    member_data = []

    for member in guild.members:
        if member.bot:
            continue
        if any(role.name in ["Member", "Alumni", "Current EXCO"] for role in member.roles):

            # Assign role conditionally
            if any(role.name == "Current EXCO" for role in member.roles):
                role_status = "Current EXCO"
            elif any(role.name == "Alumni" for role in member.roles):
                role_status = "Alumni"
            elif any(role.name == "Member" for role in member.roles):
                role_status = "Member"
            else:
                role_status = "None"

            # Determine piano-playing group based on roles
            piano_roles = ["Advanced", "Intermediate", "Novice", "Foundational"]
            piano_group = [role.name for role in member.roles if role.name in piano_roles]
            piano_group_status = ", ".join(piano_group) if piano_group else "None"

            # Append member details to the list
            member_data.append({
                'Discord_Username': member.name,
                'Name': member.nick or "None",
                'Role': role_status,
                'Piano_Playing_Group': piano_group_status,
                'Joined_Server_Time': member.joined_at.strftime("%Y-%m-%d %H:%M:%S")
            })
    
    df = pd.DataFrame(member_data)
    excel_filename = 'members_details.xlsx'
    df.to_excel(excel_filename, index=False)

    # Load the workbook and convert the sheet to a table
    wb = load_workbook(excel_filename)
    ws = wb.active

    # Define the table range and name
    table_ref = f"A1:{chr(64 + len(df.columns))}{len(df) + 1}"
    table = Table(displayName="MemberTable", ref=table_ref)

    # Add style to the table
    style = TableStyleInfo(name="TableStyleLight18", showFirstColumn=False,
                        showLastColumn=False, showRowStripes=True, showColumnStripes=False)
    table.tableStyleInfo = style

    # Auto-adjust column widths
    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
        column_letter = get_column_letter(column_cells[0].column)
        ws.column_dimensions[column_letter].width = length + 2

    # Add the table and save the workbook
    ws.add_table(table)
    wb.save(excel_filename)

    await ctx.send("Details relating to members and alumni have been exported to an Excel file.", file=discord.File(excel_filename))
    os.remove(excel_filename)


bot.run(token)