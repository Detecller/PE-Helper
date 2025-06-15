import discord
from discord.ext import commands
from discord import app_commands
from utils.audio_essentials import *
from youtubesearchpython import VideosSearch

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
        intChannel = interaction.channel
        user_id = interaction.user.id
        if user_id in self.voted_skip:
            return
        member_ids = self.currently_playing['members']
        if user_id not in member_ids:
            return
        self.voted_skip.append(user_id)
        if user_id in self.voted_continue:
            self.voted_continue.remove(user_id)
        embed = discord.Embed(title="Vote Skip", description=f"Vote to skip {self.currently_playing['title']}")
        embed.add_field(name="⏩ Skip", value=f"{len(self.voted_skip)} Voted", inline=True)
        embed.add_field(name="▶️ Continue", value=f"{len(self.voted_continue)} Voted", inline=True)
        message = await self.interaction.original_response()
        await interaction.response.send_message("Successfully voted to skip", ephemeral=True)
        await message.edit(embed=embed)
        if (len(self.voted_skip) > len(self.currently_playing['members'])/2):
            await intChannel.send(f"{self.currently_playing['title']} will be skipped")


    @discord.ui.button(label="▶️ Continue", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.Button):
        user_id = interaction.user.id
        if user_id in self.voted_continue:
            return
        member_ids = self.currently_playing['members']
        if user_id not in member_ids:
            return
        self.voted_continue.append(user_id)
        if user_id in self.voted_skip:
            self.voted_skip.remove(user_id)
        embed = discord.Embed(title="Vote Skip", description=f"Vote to skip {self.currently_playing['title']}")
        embed.add_field(name="⏩ Skip", value=f"{len(self.voted_skip)} Voted", inline=True)
        embed.add_field(name="▶️ Continue", value=f"{len(self.voted_continue)} Voted", inline=True)
        message = await self.interaction.original_response()
        await interaction.response.send_message("Successfully voted to continue", ephemeral=True)
        await message.edit(embed=embed)


class MusicBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="join-vc", description="Get PE Helper to join a vc")
    async def join_vc(interaction: discord.Interaction):
        user_vc = interaction.user.voice
        if not user_vc:
            await interaction.response.send_message(f"You need to be in a Voice Channel to perform this command")
            return
        voice_client = interaction.guild.voice_client
        voice_channel = user_vc.channel
        if voice_client and voice_client.is_playing() or video_queue:
            await interaction.response.send_message(f"PE Helper is already playing in <#{voice_client.channel.id}>")
            return
        if voice_client and voice_channel != voice_client.channel:
            await voice_client.disconnect()
        await voice_channel.connect(self_deaf=True, self_mute=False)
        await interaction.response.send_message(f"Joined VC <#{voice_channel.id}>!")

    @app_commands.command(name="add-queue", description="Add a song to the queue")
    async def add_queue(interaction: discord.Interaction, search: str):
        user_vc = interaction.user.voice
        if not user_vc:
            await interaction.response.send_message(f"You need to be in a VC to perform this command")
            return
        if len(video_queue) >= 10:
            await interaction.response.send_message(f"Only 10 songs can be added to queue")
            return
        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.send_message(f"Bot has not joined a VC yet")
            return
        if user_vc.channel != voice_client.channel:
            await interaction.response.send_message(
                "You need to be in the same VC as PE Helper to perform this command")
            return
        await interaction.response.defer()
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
            youtube = googleapiclient.discovery.build(
                'youtube', 'v3', developerKey=youtube_api_key
            )
            request = youtube.videos().list(part="snippet, contentDetails", id=video_id)
            response = request.execute()
            video = response['items'][0]['snippet']
            title = video['title']
            link = search
            duration = response['items'][0]['contentDetails']['duration'][2:]
            split_dura = duration.split('M')
            minutes = split_dura[0]
            seconds = split_dura[:-1]
            duration = f"{minutes}:{seconds}"
            path = get_audio(link)
            videoInfo = {'title': title, 'link': link, 'id': video_id, 'path': path, 'duration': duration,
                         'displayTitle': video['title']}

        video_queue.append(videoInfo)
        await interaction.followup.send(f"Added: {videoInfo['title']}\nLink: {video['link']} - {video['duration']}")

    @app_commands.command(name="view-queue", description="View all songs in a queue")
    async def view_queue(interaction: discord.Interaction):
        if currently_playing:
            queue_info = [currently_playing] + video_queue
        else:
            queue_info = video_queue

        def formatting(info):
            return f"{info['displayTitle']} - {info['duration']}\nLink: {info['link']}"

        embed = discord.Embed(title="Music Queue", description="\n\n".join(
            [f"{formatting(i)}" if idx == 0 else f"{idx}: {formatting(i)}" for idx, i in enumerate(queue_info)]))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="vote-skip", description="Vote to skip a song")
    async def vote_skip(interaction: discord.Interaction):
        instanceVoteCheck = [i for i in VoteSkip.instances if i['id'] == currently_playing['id']]
        embed = discord.Embed(title="Vote Skip", description=f"Vote to skip {currently_playing['title']}")
        if not instanceVoteCheck:
            view = VoteSkip(currently_playing, interaction)
            embed.add_field(name="⏩ Skip", value=f"0 Voted", inline=True)
            embed.add_field(name="▶️ Continue", value=f"0 Voted", inline=True)
        else:
            view = instanceVoteCheck[0]['instance']
            embed.add_field(name="⏩ Skip", value=f"{len(view.voted_skip)} Voted", inline=True)
            embed.add_field(name="▶️ Continue", value=f"{len(view.voted_continue)} Voted", inline=True)
        await interaction.response.send_message(embed=embed, view=view)