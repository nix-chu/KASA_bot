from dotenv import load_dotenv
from discord.ext import commands, tasks
import tweepy
import os

class KASA_bot(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.twitter_api = None

        self.twitter_accounts = [
            {
                "username": "yenankles"
            }
        ]
        # TODO: Need to connect username with Discord channel
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Prepare bot functionality on start-up."""
        self.startup_twitter_update()

        # Load background tasks
        self.check_twitter_update.start()

        # Start-up complete message
        print("Bot is online")

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

    @tasks.loop(minutes=1)
    async def check_twitter_update(self):
        """Periodically check for twitter updates every minute for every user."""
        for user in self.twitter_accounts:
            tweets = self.twitter_api.user_timeline(
                screen_name=user["username"],
                count=10,
                exclude_replies=True,
                include_rts=False
            )

            for i in range(len(tweets) - 1, -1, -1):
                if user["last_tweet_id"] < tweets[i].id:
                    # There is a new tweet
                    print(tweets[i].text) # TODO: Create embed for every new tweet and post on channel
                    user["last_tweet_id"] = tweets[i].id

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("shut up")

def setup(client):
    """Initialises the class inside the Discord bot."""
    client.add_cog(KASA_bot(client))

if __name__ == "__main__":
    kasa_bot = KASA_bot(commands.Bot(command_prefix="k/"))