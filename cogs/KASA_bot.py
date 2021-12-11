from dotenv import load_dotenv
from discord import Embed
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

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("shut up")

def setup(client):
    """Initialises the class inside the Discord bot."""
    client.add_cog(KASA_bot(client))

if __name__ == "__main__":
    kasa_bot = KASA_bot(commands.Bot(command_prefix="k/"))