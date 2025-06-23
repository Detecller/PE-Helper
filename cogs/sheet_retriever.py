import discord
from discord.ext import commands
from discord import app_commands, Object
from utils.permissions import has_allowed_role_and_channel
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os
import logging
from utils.setup_logger import log_slash_command
import io
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials


GUILD_ID = int(os.getenv("GUILD_ID"))
MUSIC_SHEETS_FOLDER_ID = str(os.getenv("MUSIC_SHEETS_FOLDER_ID"))
SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_JSON = 'auth/token.json'
CREDENTIALS_FILE = 'auth/credentials.json'

# Get logger
logger = logging.getLogger("pe_helper")


def list_folder_contents(service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, shortcutDetails)"
    ).execute()
    items = results.get('files', [])
    files = []

    for item in items:
        if item['mimeType'] != 'application/vnd.google-apps.folder':
            files.append({
                "name": item["name"],
                "id": item["id"]
            })

        # If the item is a folder, recurse into it
        if item["mimeType"] == "application/vnd.google-apps.folder":
            files.extend(list_folder_contents(service, item['id']))

    return files


class SheetDownloadButton(discord.ui.Button):
    def __init__(self, label, file_id, service):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.file_id = file_id
        self.service = service

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            # Get file metadata first to check MIME type
            file_metadata = self.service.files().get(fileId=self.file_id, fields='name, mimeType').execute()
            mime_type = file_metadata.get('mimeType')

            file_stream = io.BytesIO()

            if mime_type.startswith('application/vnd.google-apps'):
                # Google Docs format - use export endpoint
                export_mime = 'application/pdf'
                request = self.service.files().export_media(fileId=self.file_id, mimeType=export_mime)
            else:
                # Binary file - download directly
                request = self.service.files().get_media(fileId=self.file_id)

            downloader = MediaIoBaseDownload(file_stream, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            file_stream.seek(0)
            await interaction.followup.send(
                content=f"Here is your requested music sheet: **{self.label}**",
                file=discord.File(fp=file_stream, filename=f"{self.label}.pdf"),
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                content=f"❌ Failed to download {self.label}: {e}",
                ephemeral=True
            )


class SheetRetriever(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    sheet_retriever_group = app_commands.Group(name="sheet-retriever", description="Sheet-retrieving commands")


    @sheet_retriever_group.command(name="view-pe-sheets", description="View music sheets available in PE's catalog.")
    @has_allowed_role_and_channel(allowed_channels=['📖┃music-sheets', '🚧┃test-commands'])
    async def view_pe_sheets(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        log_slash_command(logger, interaction)

        creds = None
        # Load saved credentials if available
        if os.path.exists(TOKEN_JSON):
            creds = Credentials.from_authorized_user_file(TOKEN_JSON, SCOPES)
        # If no valid credentials, start OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for next run
            with open(TOKEN_JSON, 'w') as token:
                token.write(creds.to_json())

        # Build the Drive service
        service = build('drive', 'v3', credentials=creds)

        files = list_folder_contents(service, folder_id = MUSIC_SHEETS_FOLDER_ID)
        if not files:
            await interaction.followup.send("No music sheets found.", ephemeral=True)
            return

        embed = discord.Embed(title="🎵  PE's Music Sheet Catalog", color=discord.Color.blue())
        embed.set_footer(text="Select a sheet to download.")

        view = discord.ui.View()
        for i, f in enumerate(files):
            button = SheetDownloadButton(f["name"], f["id"], service)
            button.row = i
            view.add_item(button)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SheetRetriever(bot), guild=Object(id=GUILD_ID))