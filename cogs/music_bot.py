import discord
from discord.ext import commands
from discord import app_commands, Object
from utils.audio_essentials import *
from youtubesearchpython import VideosSearch
from utils.permissions import has_allowed_role_and_channel
import logging


GUILD_ID = int(os.getenv("GUILD_ID"))
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Get logger
logger = logging.getLogger("pe_helper")


class VoteSkip(discord.ui.View):
    instances = []
    def __init__(self, currently_playing, interaction):
        super().__init__()
        self.interaction = interaction
        self.currently_playing = currently_playing
        self.voted_skip = []
        self.voted_continue = []
        self.instances.append({'instance': self, 'id': currently_playing['id']})
        self.majority = (len(self.voted_skip) > len(self.currently_playing['members'])/2)


    @discord.ui.button(label="⏩ Skip", style=discord.ButtonStyle.green)
    async def skip(self, interaction: discord.Interaction, button: discord.Button):

        user_id = interaction.user.id
        
        if user_id in self.voted_skip:
            return
        if user_id not in self.currently_playing['members']:
            return
        self.voted_skip.append(user_id)
        if user_id in self.voted_continue:
            self.voted_continue.remove(user_id)

        logger.info(f"{interaction.user} voted to skip {self.currently_playing['title']}")
        embed = discord.Embed(title="Vote Skip", description=f"Vote to skip {self.currently_playing['title']}")
        embed.add_field(name="⏩ Skip", value=f"{len(self.voted_skip)} Voted", inline=True)
        embed.add_field(name="▶️ Continue", value=f"{len(self.voted_continue)} Voted", inline=True)
        message = await self.interaction.original_response()
        await interaction.response.send_message("Successfully voted to skip", ephemeral=True)
        await message.edit(embed=embed)

        if len(self.voted_skip) > len(self.currently_playing['members'])/2:
            await interaction.channel.send(f"{self.currently_playing['title']} will be skipped")
            logger.info(f"Majority reached, skipping song: {self.currently_playing['title']}")


    @discord.ui.button(label="▶️ Continue", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.Button):
        user_id = interaction.user.id
        if user_id in self.voted_continue:
            return
        if user_id not in self.currently_playing['members']:
            return
        self.voted_continue.append(user_id)
        if user_id in self.voted_skip:
            self.voted_skip.remove(user_id)
        logger.info(f"{interaction.user} voted to continue {self.currently_playing['title']}")
        embed = discord.Embed(title="Vote Skip", description=f"Vote to skip {self.currently_playing['title']}")
        embed.add_field(name="⏩ Skip", value=f"{len(self.voted_skip)} Voted", inline=True)
        embed.add_field(name="▶️ Continue", value=f"{len(self.voted_continue)} Voted", inline=True)
        message = await self.interaction.original_response()
        await interaction.response.send_message("Successfully voted to continue", ephemeral=True)
        await message.edit(embed=embed)


class MusicBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    music_group = app_commands.Group(name="music", description="Music commands")


    @music_group.command(name="add-queue", description="Add a song to the queue")
    @has_allowed_role_and_channel(allowed_channels=['🎶┃music-radio-tools', '🚧┃test-commands'])
    async def add_queue(self, interaction: discord.Interaction, search: str):

        user_vc = interaction.user.voice
        
        if not user_vc:
            logger.warning(f"{interaction.user} attempted to add queue without VC")
            await interaction.response.send_message(f"You need to be in a VC to perform this command")
            return
        if len(video_queue) >= 10:
            await interaction.response.send_message(f"Only 10 songs can be added to queue.")
            return
        
        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.send_message(f"Bot has not joined VC.")
            return
        if user_vc.channel != voice_client.channel:
            await interaction.response.send_message("You need to be in the same VC as PE Helper to perform this command.")
            return
        
        await interaction.response.defer()

        try:
            if not any([regex.search(search) for regex in regexs]):
                video_search = VideosSearch(search, limit=1)
                video = video_search.result()['result'][0]
                video_id = video["id"]
                if not check_video_length(video_id):
                    await interaction.response.send_message("Only songs under 1 hour can be played")
                    return
                path = get_audio(video['link'])
                videoInfo = {'title': video['title'], 'link': video['link'], 'id': video_id, 'path': path,
                            'duration': video['duration'], 'displayTitle': video['title']}
            else:
                video_id = get_id(search)
                youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
                request = youtube.videos().list(part="snippet, contentDetails", id=video_id)
                response = request.execute()
                video = response['items'][0]['snippet']
                title = video['title']
                link = search
                duration = response['items'][0]['contentDetails']['duration']
                path = get_audio(link)
                videoInfo = {'title': title, 'link': link, 'id': video_id, 'path': path, 'duration': duration,
                            'displayTitle': title}
                
            video_queue.append(videoInfo)
            logger.info(f"Added to queue: {videoInfo['title']} ({videoInfo['duration']}) by {interaction.user}")
            await interaction.followup.send(f"Added: {videoInfo['title']}\nLink: {videoInfo['link']} - {videoInfo['duration']}")
            refresh_song(self.bot, GUILD_ID)
            
        except Exception as e:
            logger.error(f"Failed to add song to queue: {e}", exc_info=True)
            await interaction.followup.send("An error occurred while adding the song.")


    @music_group.command(name="view-queue", description="View all songs in a queue")
    @has_allowed_role_and_channel(allowed_channels=['🎶┃music-radio-tools', '🚧┃test-commands'])
    async def view_queue(self, interaction: discord.Interaction):
        if currently_playing:
            queue_info = [currently_playing] + video_queue
        else:
            queue_info = video_queue
        
        if not queue_info:
            await interaction.response.send_message("There are no songs in the queue.")
            return

        def formatting(info):
            return f"{info['displayTitle']} - {info['duration']}\nLink: {info['link']}"

        embed = discord.Embed(title="Music Queue", description="\n\n".join(
            [f"{formatting(i)}" if idx == 0 else f"{idx}: {formatting(i)}" for idx, i in enumerate(queue_info)]))
        logger.info(f"{interaction.user} viewed the music queue")
        await interaction.response.send_message(embed=embed)


    @music_group.command(name="vote-skip", description="Vote to skip a song")
    @has_allowed_role_and_channel(allowed_channels=['🎶┃music-radio-tools', 'test-commands'])
    async def vote_skip(self, interaction: discord.Interaction):
        if not currently_playing:
            await interaction.response.send_message("No song is currently playing.")
            return
        instanceVoteCheck = [i for i in VoteSkip.instances if i['id'] == currently_playing['id']]
        embed = discord.Embed(title="Vote Skip", description=f"Vote to skip {currently_playing['title']}")
        if not instanceVoteCheck:
            view = VoteSkip(currently_playing, interaction)
            embed.add_field(name="⏩ Skip", value="0 Voted", inline=True)
            embed.add_field(name="▶️ Continue", value="0 Voted", inline=True)
        else:
            view = instanceVoteCheck[0]['instance']
            embed.add_field(name="⏩ Skip", value=f"{len(view.voted_skip)} Voted", inline=True)
            embed.add_field(name="▶️ Continue", value=f"{len(view.voted_continue)} Voted", inline=True)
        logger.info(f"{interaction.user} initiated or joined vote-skip for: {currently_playing['title']}")
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicBot(bot), guild=Object(id=GUILD_ID))