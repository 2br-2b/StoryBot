#import pkg_resources
#pkg_resources.require("discord.py==1.7.3")

import discord


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



import dmlistener
from user_manager import user_manager
from file_manager import file_manager
from discord.ext import commands
from threading import Thread
import time

intents = discord.Intents.default()
intents.message_content = True


bot = commands.Bot(config.PREFIX, help_command = None, intents=intents)

fmgr = file_manager(bot)
umgr = user_manager(bot)

dml = dmlistener.dmlistener(fmgr, umgr, bot)
bot.file_manager = fmgr
bot.user_manager = umgr


@bot.event
async def on_ready():
    print("Bot started!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=" for `"+config.PREFIX+"help`"))
    try:
        await bot.load_extension("dmlistener")
    except commands.errors.ExtensionNotFound:
        print("Failed to load dmlistener!")
    except commands.errors.ExtensionAlreadyLoaded:
        pass
    except commands.errors.NoEntryPointError:
        print("Put the setup() function back fool.")

if(config.TOKEN == 'xxxxxxxxxxxxx'):
    raise RuntimeError("Please update config.py with your bot's token!")

bot.run(config.TOKEN)