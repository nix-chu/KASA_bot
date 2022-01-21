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

    async def join(self, ctx):
        """Join a voice channel."""
        if ctx.author.voice is None:
            # User is not in a voice channel
            await ctx.send("You're not in a voice channel!")
            return

        voice_channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            # Bot is not connected to any voice channel
            await ctx.voice_client.connect(voice_channel)
        elif ctx.voice_client.channel == voice_channel:
            # Bot is already connected to your voice channel
            return
        else:
            # User and bot are in different voice channels
            await ctx.voice_client.move_to(voice_channel)
    
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

    @commands.command()
    async def play(self, ctx, url): 
        """Add a song to queue."""
        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        self.join()

        # TODO: Check if url is from youtube and reject otherwise

        # Download song info
        download_info = self.music_downloader.extract_info(url, download=False)
        download_url = download_info['formats'][0]['url']
        song_title = download_info['title']
        source = await FFmpegOpusAudio.from_probe(download_url, **FFMPEG_OPTIONS)
        
        # Add song to server's queue
        guild_id = ctx.message.guild.id
        if guild_id in self.queues:
            self.queues[guild_id].append(
                {
                    "song_title": song_title,
                    "song":source
                }
            )
        else:
            self.queues[guild_id] = [
                {
                    "song_title": song_title,
                    "song": source
                }
            ]
        
        if ctx.voice_client.is_playing():
            # Announce song added to queue
            await ctx.send(song_title + " added to queue!")
        else:
            # Play song
            await next(ctx)


    @commands.command()
    async def next(self, ctx):
        """Play the next song in queue."""
        voice = ctx.guild.voice_client
        voice.stop()

        guild_id = ctx.message.guild.id
        if self.queues[guild_id] != []:
            song_dict = self.queues[guild_id].pop(0)
            voice.play(song_dict["song"], after=lambda x = None : self.next(ctx))
            await ctx.send(song_dict["song_title"] + " now playing!")
        else:
            await ctx.send("No songs left in queue.")

    @commands.command()
    async def pause(self, ctx):
        """Pause the current song."""
        await ctx.voice_client.pause()
        await ctx.send("Paused song.")
    
    @commands.command()
    async def resume(self, ctx):
        """Resumes the paused song."""
        await ctx.voice_client.resume()
        await ctx.send("Resumed song.")

    # End of Youtube commands

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("Bot version is 220121.1")

def setup(client):
    """Initialises the class inside the Discord bot."""
    client.add_cog(KASA_bot(client))

if __name__ == "__main__":
    kasa_bot = KASA_bot(commands.Bot(command_prefix="k/"))