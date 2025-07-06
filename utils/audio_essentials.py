import yt_dlp
import re
import os
from dotenv import load_dotenv
import googleapiclient.discovery
import discord
from utils.variables import currently_playing, audio
import logging
import platform
import traceback


load_dotenv()
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

os_type = platform.system()
if os_type == "Windows":
    FFMPEG_PATH = os.getenv('FFMPEG_PATH_LOCAL')
elif os_type == "Linux":
    FFMPEG_PATH = os.getenv('FFMPEG_PATH_VPS')

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

        ydl_opts = {
            'user_agent': 'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'format': 'bestaudio[acodec=opus]/bestaudio[ext=webm]/bestaudio/best',
            'outtmpl': 'audios/%(title)s.opus',
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'auth/cookies.txt',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info_dict)
            audio_file = filepath
            logger.info(f"Downloaded audio to: {audio_file}")
            return audio_file

    except Exception as e:
        logger.error(f"Failed to download audio from {url}: %s\n%s", e, traceback.format_exc(), extra={"category": ["music_bot", "get_audio"]})
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
        logger.error(f"Error extracting video ID from {url}:: %s\n%s", e, traceback.format_exc(), extra={"category": ["music_bot", "get_id"]})
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
        logger.info(f"Video duration for {VidID}: {duration}", extra={"category": ["music_bot", "check_video_length"]})
        return "H" not in duration
    except Exception as e:
        logger.error(f"Error checking video length for {VidID}:: %s\n%s", e, traceback.format_exc(), extra={"category": ["music_bot", "check_video_length"]})
        return False


def refresh_song(client, set_guild):
    global currently_playing
    global audio

    try:
        guild = client.get_guild(set_guild)
        voice_client = guild.voice_client
        if not voice_client:
            logger.warning(f"No voice client found for guild {set_guild}", extra={"category": ["music_bot", "refresh_song"]})
            return
        if voice_client.is_playing():
            logger.debug("Voice client is already playing")
            return

        if not video_queue:
            logger.info("No songs left in queue")
            currently_playing.clear()
            return
        
        # Clean up the previous song file if it exists (before starting new song)
        if currently_playing and os.path.exists(currently_playing['path']):
            try:
                os.remove(currently_playing['path'])
                logger.info(f"Cleaned up previous audio file: {currently_playing['path']}")
            except Exception as e:
                logger.warning(f"Error deleting previous audio file: %s\n%s", e, traceback.format_exc(), extra={"category": ["music_bot", "refresh_song"]})

        # Pop next song before playing
        next_song = video_queue.pop(0)
        currently_playing.clear()
        currently_playing.update(next_song)
        currently_playing['displayTitle'] = f"Currently Playing: {next_song['title']}"

        # Get members currently in VC (excluding bot)
        voice_client_channel = voice_client.channel
        vc_member_ids = [member.id for member in voice_client_channel.members if member.id != client.user.id]
        currently_playing['members'] = vc_member_ids
        logger.info(f"Now playing: {next_song['title']} with VC members {vc_member_ids}")

        def after_playing(error):
            global currently_playing
            try:
                if currently_playing and os.path.exists(currently_playing['path']):
                    os.remove(currently_playing['path'])
                    logger.info(f"Deleted file after playback: {currently_playing['path']}")
            except Exception as e:
                logger.warning(f"Failed to delete after playback:: %s\n%s", e, traceback.format_exc(), extra={"category": ["music_bot", "refresh_song"]})
            # Try to play the next song
            refresh_song(client, set_guild)
        
        # Set perceived loudness, true peak limit & loudness range
        ffmpeg_options = {
            'options': '-vn -af loudnorm=I=-22:TP=-1.5:LRA=11'
        }

        audio = discord.FFmpegOpusAudio(source=next_song['path'], executable=FFMPEG_PATH, **ffmpeg_options)
        voice_client.play(audio, after=lambda e: after_playing(e))

    except Exception as e:
        logger.error(f"Error in refresh_song:: %s\n%s", e, traceback.format_exc(), extra={"category": ["music_bot", "refresh_song"]})
        return