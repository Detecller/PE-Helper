from pytubefix import YouTube
import re
import os
from dotenv import load_dotenv
import googleapiclient.discovery
import discord

load_dotenv()
youtube_api_key = os.getenv('YOUTUBE_API_KEY')


currently_playing = None
audio = None
video_queue = []

valid_links = ['youtube.com', 'youtu.be']
regexs = [re.compile(i) for i in valid_links]

def create_directory(name):
    try:
        os.makedirs(name)
    except FileExistsError:
        pass
    return

def get_audio(url):
    create_directory("audios")
    video = YouTube(url).streams.filter(only_audio=True).first().download(output_path="audios")
    return video

def get_id(url):
    watchcheck = re.compile("watch")
    if watchcheck.search(url):
        check = url.split('=')[-1]
        return check
    check = url.split('?')[0]
    check = check.split('/')[-1]
    return check

def check_video_length(VidID):
    youtube = googleapiclient.discovery.build(
        'youtube', 'v3', developerKey=youtube_api_key
    )
    requests = youtube.videos().list(part="id, contentDetails", id=VidID)
    response = requests.execute()
    duration = response['items'][0]['contentDetails']['duration']
    if "H" in duration:
        return False
    return True


def refresh_song(client, set_guild):
    global currently_playing
    global audio
    try:
        guild = client.get_guild(set_guild)
        voice_client = guild.voice_client
        if not voice_client: return
        if voice_client.is_playing(): return
        try:
            if currently_playing:
                os.remove(currently_playing['path'])
                print("Removed Song")
        except Exception as e:
            pass
        if not video_queue: return
        executable_path = r"<insert path here>"
        audio = discord.FFmpegPCMAudio(executable=executable_path, source=video_queue[0]['path'])
        voice_client.play(audio)
        currently_playing = None if not video_queue else video_queue[0]
        currently_playing['displayTitle'] = f"Currently Playing: {currently_playing['title']}"
        voice_client_channel = voice_client.channel
        vc_member_ids = [member.id for member in voice_client_channel.members if member.id != client.user.id]
        currently_playing['members'] = vc_member_ids
        video_queue.pop(0)
    except Exception as e:
        return