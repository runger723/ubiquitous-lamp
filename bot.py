# bot.py
import os
import random
import asyncio
import queue
import json
import ffmpeg


import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time

import discord
from dotenv import load_dotenv
from discord.ext import commands

from youtube_search import YoutubeSearch
import youtube_dl

####
#### Global Variable Declaration
####

#load environment variables and sensitive information
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
spot_username = os.getenv('username')
spot_client_id = os.getenv('client_id')
spot_client_secret = os.getenv('client_secret')

print("\n Loaded Environment Variables \n")

#Connect to Spotify
client_credentials_manager = SpotifyClientCredentials(spot_client_id, spot_client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
baseFiles = ['.env', 'bot.py', 'scratch.txt', 'test.py', 'env', '.git']
path = os.getenv('path')

print("\n Used Spotify Credentials \n")

songQueue = queue.SimpleQueue()
songQueueCopy = queue.SimpleQueue()

players = {}


#Create initial bot and set prefix
bot = commands.Bot(command_prefix = '$')

####
#### youtube_dl settings
####

youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)



####
#### Function Declarations
####

#Takes a Spotify playlist and returns a list of tuples containing title and artist
async def getTracks(playlist_id):
    tracks = []
    playlist = sp.playlist(playlist_id)
    for item in playlist['tracks']['items']:
        track = (item['track'])
        tracks.append((track['name'], track['artists'][0]['name']))
    return tracks

#Takes a list of tracks from getTracks, finds youtube links, and puts into queue
async def addTracksToQueue(tracklist):
    for song in tracklist:
        searchTerm = ""
        searchTerm = str(song[0]) + " by " + str(song[1])
        results = await YoutubeSearch(searchTerm, max_results=1).to_json()
        await songQueue.put(json.loads(results)['videos'][0]["url_suffix"])

#downloads youtube video from URL and returns FFmpeg file
async def from_url(url):
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url))

    if 'entries' in data:
        data = data['entries'][0]

    filename = ytdl.prepare_filename(data)
    print(filename)
    print('\n')

    return discord.FFmpegPCMAudio(filename, **ffmpeg_options)

#Cleans old audio files from folder
async def cleanUp(path, baseFiles):
    for item in os.listdir(path):
        if item not in baseFiles:
            try:
                os.remove(item)
            except:
                print("\n Cleanup of " + str(item) + " was skipped \n")


####
#### Discord Bot Commands
####

#Announces successful discord connection
@bot.event
async def on_ready():
    assigned = False
    print(f'{bot.user.name} has connected to Discord!')

#Takes a spotify playlist and sends them to be searched and queued
@bot.command(name='playlist')
async def queue_spotify_list(ctx, playlist_url):
    playlist_id = playlist_url
    tracklist = await getTracks(playlist_id)
    addTracksToQueue(tracklist)

@bot.command(name='pause')
async def pauseBot(ctx):
    channel = ctx.author.voice.channel
    try:
        vc = players[channel]
        vc.pause()
    except:
        ctx.send("Player not found")

@bot.command(name='play')
async def playBot(ctx):
    channel = ctx.author.voice.channel
    try:
        vc = players[channel]
        vc.resume()
    except:
        ctx.send("Player not found")

#Searches YouTube for a term, calls from_url, downloads audio, plays on voice channel
@bot.command(name='yt')
async def playYTVideo(ctx, *, searchTerm: str):
    results = YoutubeSearch(searchTerm, max_results=1).to_json()
    songQueue.put(json.loads(results)['videos'][0]["url_suffix"])

    channel = ctx.author.voice.channel

    await cleanUp(path, baseFiles)

    try:
        vc = players[channel]
    except:
        vc = await channel.connect()
        players[channel] = vc

    vidurl = "youtube.com" + str(songQueue.get())

    print(vidurl)
    player = await from_url(vidurl)
    try:
        vc.play(player)
    except:
        vc.stop()
        vc.play(player)




####
#### Start Bot
####
print("\n Starting Bot \n")

bot.run(TOKEN)
