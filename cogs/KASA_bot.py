from dotenv import load_dotenv
from discord.ext import commands, tasks
import tweepy
import os

class KASA_bot(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.twitter_api = None
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Prepare bot functionality on start-up."""

        # Start-up Twitter portion of bot
        load_dotenv(".env")
        consumer_key = os.getenv('TW_CONSUMER_KEY')
        consumer_secret = os.getenv('TW_CONSUMER_SECRET')
        twitter_token = os.getenv('TWITTER_TOKEN')
        twitter_token_secret = os.getenv('TWITTER_TOKEN_SECRET')

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(twitter_token, twitter_token_secret)
        self.twitter_api = tweepy.API(auth)

        # Load background tasks
        self.check_twitter_update.start()

        # Start-up complete message
        print("Bot is online")

    @tasks.loop(minutes=1)
    async def check_twitter_update(self):
        print("yes")

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("shut up")

def setup(client):
    """Initialises the class inside the Discord bot."""
    client.add_cog(KASA_bot(client))