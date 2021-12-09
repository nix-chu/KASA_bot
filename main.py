from dotenv import load_dotenv
from discord.ext import commands
import os

client = commands.Bot(command_prefix="k/")

@client.command()
async def load(ctx, extension):
    """Add a Class of commands onto the bot."""
    client.load_extension(f'cogs.{extension}')

@client.command()
async def unload(ctx, extension):
    """Remove a Class of commands from the bot."""
    client.unload_extension(f'cogs.{extension}')

@client.command()
async def reload(ctx, extension):
    """Update an existing Class of commands from the bot."""
    client.unload_extension(f'cogs.{extension}')
    client.load_extension(f'cogs.{extension}')

# Operate on bot start-up
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        client.load_extension(f'cogs.{filename[:-3]}') # Remove .py extension

load_dotenv(".env")
client.run(os.getenv('TOKEN'))
