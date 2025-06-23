from pytubefix import YouTube
import re
import os
from dotenv import load_dotenv
import googleapiclient.discovery
import discord
from utils.variables import currently_playing, audio
import logging


load_dotenv()
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
FFMPEG_PATH = os.getenv('FFMPEG_PATH')

logger = logging.getLogger("pe_helper")


video_queue = []

valid_links = ['youtube.com', 'youtu.be']
regexs = [re.compile(i) for i in valid_links]

def create_directory(name):
    try:
        os.makedirs(name)
        logger.info(f"Created directory: {name}")
    except FileExistsError:
        logger.debug(f"Directory already exists: {name}")
    return


def get_audio(url):
    try:
        create_directory("audios")
        logger.info(f"Downloading audio from URL: {url}")
        video = YouTube(url).streams.filter(only_audio=True).first().download(output_path="audios")
        logger.info(f"Downloaded audio to: {video}")
        return video
    except Exception as e:
        logger.error(f"Failed to download audio from {url}: {e}")
        raise


def get_id(url):
    try:
        watchcheck = re.compile("watch")
        if watchcheck.search(url):
            check = url.split('=')[-1]
        else:
            check = url.split('?')[0].split('/')[-1]
        logger.debug(f"Extracted video ID: {check} from {url}")
        return check
    except Exception as e:
        logger.error(f"Error extracting video ID from {url}: {e}")
        raise


def check_video_length(VidID):
    try:
        logger.debug(f"Checking video length for ID: {VidID}")
        youtube = googleapiclient.discovery.build(
            'youtube', 'v3', developerKey=YOUTUBE_API_KEY
        )
        requests = youtube.videos().list(part="id, contentDetails", id=VidID)
        response = requests.execute()
        duration = response['items'][0]['contentDetails']['duration']
        logger.info(f"Video duration for {VidID}: {duration}")
        return "H" not in duration
    except Exception as e:
        logger.error(f"Error checking video length for {VidID}: {e}")
        return False


def refresh_song(client, set_guild):
    global currently_playing
    global audio
    try:
        guild = client.get_guild(set_guild)
        voice_client = guild.voice_client
        if not voice_client:
            logger.warning(f"No voice client found for guild {set_guild}")
            return
        if voice_client.is_playing():
            logger.debug("Voice client is already playing")
            return

        if currently_playing:
            try:
                os.remove(currently_playing['path'])
                logger.info(f"Removed previously played file: {currently_playing['path']}")
            except Exception as e:
                logger.warning(f"Failed to remove file: {currently_playing['path']} — {e}")

        if not video_queue:
            logger.info("No songs left in queue")
            return

        next_song = video_queue[0]
        logger.info(f"Now playing: {next_song['title']} from {next_song['path']}")
        audio = discord.FFmpegPCMAudio(executable=FFMPEG_PATH, source=next_song['path'])
        voice_client.play(audio)

        currently_playing = video_queue.pop(0)
        currently_playing['displayTitle'] = f"Currently Playing: {currently_playing['title']}"
        voice_client_channel = voice_client.channel
        vc_member_ids = [member.id for member in voice_client_channel.members if member.id != client.user.id]
        currently_playing['members'] = vc_member_ids
        logger.info(f"Updated current song with VC members: {vc_member_ids}")
    except Exception as e:
        logger.error(f"Error refreshing song: {e}")
        return