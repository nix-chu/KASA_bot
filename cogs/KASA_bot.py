from discord.ext import commands

class KASA_bot(commands.Cog):

    def __init__(self, client):
        self.client = client
    
    @commands.Cog.listener()
    async def on_ready(self):
        """For debugging purposes."""
        print("Bot is online")
    
    @commands.command()
    async def hello(self, ctx):
        await ctx.send("shut up")

def setup(client):
    """Initialises the class inside the Discord API."""
    client.add_cog(KASA_bot(client))