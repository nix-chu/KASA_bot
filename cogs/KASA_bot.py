import asyncio
from dotenv import load_dotenv
from discord import Embed, FFmpegOpusAudio
from discord.ext import commands, tasks
import tweepy
import os
import youtube_dl

class KASA_bot(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.twitter_api = None
        self.music_downloader = None

        self.twitter_accounts = [
            {
                "username": "yenankles"
            }
        ]
        # TODO: Need to connect username with Discord channel

        self.queues = {}
        self.now_playing = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Prepare bot functionality on start-up."""
        self.startup_twitter_update()
        self.startup_music_player()

        # Load background tasks
        self.check_twitter_update.start()

        # Start-up complete message
        print("Bot is online")

    # Start of Twitter commands

    def startup_twitter_update(self):
        """Set-up Twitter portion of the bot."""
        
        # Load authentication keys
        load_dotenv(".env")
        consumer_key = os.getenv('TW_CONSUMER_KEY')
        consumer_secret = os.getenv('TW_CONSUMER_SECRET')
        twitter_token = os.getenv('TWITTER_TOKEN')
        twitter_token_secret = os.getenv('TWITTER_TOKEN_SECRET')

        # Activate Twitter API
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(twitter_token, twitter_token_secret)
        self.twitter_api = tweepy.API(auth)

        # Set-up self.twitter_accounts with last_tweet_id
        for user in self.twitter_accounts:
            tweet = self.twitter_api.user_timeline(
                screen_name=user["username"],
                count=1,
                exclude_replies=True,
                include_rts=False
            )
            user["last_tweet_id"] = tweet[0].id
        
        print("Twitter bot is live.")

    @tasks.loop(seconds=20)
    async def check_twitter_update(self):
        """Periodically check for twitter updates every minute for every user."""
        for user in self.twitter_accounts:
            tweets = self.twitter_api.user_timeline(
                screen_name=user["username"],
                since_id=user["last_tweet_id"], # Ensure only new tweets are received
                exclude_replies=True,
                include_rts=False
            )
            if len(tweets) > 0:
                # Iterates through new tweets. Most recent is at the front of list.
                for i in range(len(tweets) - 1, -1, -1):
                    tweet = tweets[i]
                    channel = self.client.get_channel(889045121084063814) # TODO: Add functionality to select channel

                    author_url = "https://twitter.com/" + tweet.user.screen_name
                    tweet_url = author_url + "/status/" + tweet.id_str

                    package = Embed(
                        description=tweet.text,
                        timestamp=tweet.created_at,
                        color=1942002 # Twitter blue
                    )
                    package.set_author(
                        name=tweet.user.name,
                        url=author_url,
                        icon_url=tweet.user.profile_image_url_https
                    )
                    package.set_footer(
                        text="Twitter",
                        icon_url="https://cdn4.iconfinder.com/data/icons/social-media-icons-the-circle-set/48/twitter_circle-512.png"
                    )
                    if "media" in tweet.entities.keys():
                        # Post preview regardless if video or photo or gif
                        package.set_image(url=tweet.entities["media"][0]["media_url_https"])

                    await channel.send(content=tweet_url, embed=package)
                user["last_tweet_id"] = tweets[0].id

    # End of Twitter commands
    # Start of Youtube commands

    def startup_music_player(self):
        """Set-up music player portion of the bot."""
        YDL_OPTIONS = { "format": "bestaudio" }
        self.music_downloader = youtube_dl.YoutubeDL(YDL_OPTIONS)

        print("Music bot is live")
    
    @commands.command()
    async def move(self, ctx):
        """Move bot to the user's voice channel."""
        if ctx.author.voice is None:
            # User is not in a voice channel
            await ctx.send("You're not in a voice channel!")
            return

        voice_channel = ctx.author.voice.channel
        if ctx.voice_client == voice_channel:
            await ctx.send("Bot is already in your voice channel!")
        else:
            await ctx.voice_client.move_to(voice_channel)
    
    @commands.command()
    async def disconnect(self, ctx):
        """Disconnect from a voice channel."""
        await ctx.voice_client.disconnect()

    async def join_channel(self, ctx):
        """Join a voice channel."""
        if ctx.author.voice is None:
            # User is not in a voice channel
            await ctx.send("You're not in a voice channel!")
            raise Exception("No voice channel.")

        voice_channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            # Bot is not connected to any voice channel
            await voice_channel.connect()
        elif ctx.voice_client.channel == voice_channel:
            # Bot is already connected to your voice channel
            pass
        else:
            # User and bot are in different voice channels
            await ctx.voice_client.move_to(voice_channel)

    @commands.command()
    async def play(self, ctx, url): 
        """Add a song to queue."""
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        try:
            await self.join_channel(ctx)
        except Exception as e:
            print(str(e))
            return

        # TODO: Check if url is from youtube and reject otherwise

        # Download song info
        download_info = self.music_downloader.extract_info(url, download=False)
        download_url = download_info['formats'][0]['url']
        song_title = download_info['title']
        source = await FFmpegOpusAudio.from_probe(download_url, **FFMPEG_OPTIONS)
        print("Song info downloaded.")
        
        # Add song to server's queue
        guild_id = ctx.message.guild.id
        if guild_id in self.queues:
            self.queues[guild_id].append(
                {
                    "song_title": song_title,
                    "song":source
                }
            )
            print("Song added to queue.")
        else:
            self.queues[guild_id] = [
                {
                    "song_title": song_title,
                    "song": source
                }
            ]
            print("New queue created.")
        
        if ctx.voice_client.is_playing():
            # Announce song added to queue
            await ctx.send(song_title + " added to queue!")
        else:
            # Play song
            await self.next(ctx)


    @commands.command()
    async def next(self, ctx):
        """Play the next song in queue."""
        guild_id = ctx.message.guild.id

        # Reset music player
        voice = ctx.guild.voice_client
        voice.stop()
        self.now_playing[guild_id] = None

        # Play next song
        if self.queues[guild_id] != []:
            self.now_playing[guild_id] = self.queues[guild_id].pop(0)
            voice.play(
                self.now_playing["song"],
                after=lambda x = None : asyncio.run(self.next(ctx))
            )
            await ctx.send(self.now_playing["song_title"] + " now playing!")
        else:
            try:
                await ctx.send("No songs left in queue.")
            except RuntimeError:
                await ctx.send("No songs left in queue.")
            # FIXME: Throws RuntimeError: Timeout context manager should be used inside a task. After queue finishes.

    @commands.command()
    async def pause(self, ctx):
        """Pause the current song."""
        ctx.voice_client.pause()
        await ctx.send("Paused song.")
    
    @commands.command()
    async def resume(self, ctx):
        """Resumes the paused song."""
        ctx.voice_client.resume()
        await ctx.send("Resumed song.")
    
    @commands.command()
    async def stop(self, ctx):
        """Clear queue and stop playing song."""
        ctx.guild.voice_client.stop()
        # FIXME: Throws RuntimeError: got Future pending attached to a different loop. When music player stops.
        guild_id = ctx.message.guild.id
        self.queues[guild_id] = []
        self.now_playing[guild_id] = None
        await ctx.send("Queue cleared.")

    @commands.command()
    async def queue(self, ctx):
        """View music queue."""
        guild_id = ctx.message.guild.id
        queue = self.queues[guild_id]

        if (queue is None) or (queue == []):
            await ctx.send("Queue is empty.")
            return

        # Create embed text
        text = "Coming up next:\n"
        count = 1
        for item in queue:
            text += "[" + str(count) + "] " + item["song_title"] + "\n"
            count += 1
        package = Embed(description=text)
        await ctx.send(embed=package)
    
    @commands.command()
    async def np(self, ctx):
        """Display current song playing. Also known as 'Now Playing'."""
        guild_id = ctx.message.guild.id

        if self.now_playing[guild_id] is None:
            pass
        else:
            await ctx.send("Now playing: " + self.now_playing[guild_id]["song_title"])

    # End of Youtube commands

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("Bot version is 220121.1")

def setup(client):
    """Initialises the class inside the Discord bot."""
    client.add_cog(KASA_bot(client))

if __name__ == "__main__":
    kasa_bot = KASA_bot(commands.Bot(command_prefix="k/"))