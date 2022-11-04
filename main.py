import discord
from pathlib import Path

# create the necessary files if they don't exist
try:
    import config
except ModuleNotFoundError:
    # Check if the file exists
    # If it doesn't, copy the example file
    from os.path import exists
    if not exists("config.py"):
        import shutil
        shutil.copyfile("config.py.default", "config.py")
        print("Please edit your config file (config.py) and then restart the bot.")
        exit()
    else:
        print("Something went wrong importing the config file. Check your config file for any errors, then restart the bot.")
        exit()


if not Path("story.txt").is_file():
    print("Created story.txt")
    open("story.txt", "x").close()

if not Path("user.txt").is_file():
    print("Created user.txt")
    with open("user.txt", "w") as f:
        f.write(str(config.DEFAULT_USER_IDS[0]))
        
import cogs.dm_listener as dm_listener
from user_manager import user_manager
from file_manager import file_manager
from discord.ext import commands
from threading import Thread
import time
import asyncio

intents = discord.Intents.default()
intents.message_content = True

class StoryBot(commands.Bot):
    async def setup_hook(self):
        await load_cogs(self, ["cogs.dm_listener"])
        bot.tree.copy_global_to(guild=discord.Object(id=config.GUILD_ID))
        await bot.tree.sync(guild=discord.Object(id=config.GUILD_ID))


bot = StoryBot(config.PREFIX, help_command = None, intents=intents)

fmgr = file_manager()
umgr = user_manager(bot)
dml = dm_listener.dm_listener(fmgr, umgr, bot)

bot.file_manager = fmgr
bot.user_manager = umgr


@bot.event
async def on_ready():
    print("Bot started!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=" for `"+config.PREFIX+"help`"))

if(config.TOKEN == 'xxxxxxxxxxxxx'):
    raise RuntimeError("Please update config.py with your bot's token!")


async def load_cogs(bot: commands.Bot, cog_list: list):
    for cog_name in cog_list:
        try:
            await bot.load_extension(cog_name)
        except commands.errors.ExtensionNotFound:
            print("Failed to load dm_listener for " + cog_name)
        except commands.errors.ExtensionAlreadyLoaded:
            pass
        except commands.errors.NoEntryPointError:
            print("Put the setup() function back in " + cog_name + " fool.")


bot.run(config.TOKEN)

