import pkg_resources
pkg_resources.require("discord.py==1.7.3")

import discord


try:
    import config
except ImportError:
    # Check if the file exists
    # If it doesn't, copy the example file
    from os.path import exists
    if not exists("config.py"):
        import shutil
        shutil.copyfile("config.py.default", "config.py")
        print("Please edit your config file (config.py) and then restart the bot.")
        exit()
    else:
        print("Something went wrong importing the config file. Check your config file for any errors.")
        exit()


import dmlistener
from user_manager import user_manager
from file_manager import file_manager
from discord.ext import commands
from threading import Thread
import time





bot = commands.Bot("s.", help_command = None)

f = file_manager()
u = user_manager()

dml = dmlistener.dmlistener(f, u, bot)
bot.add_cog(dml)

@bot.event
async def on_ready():
    print("Bot started!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=" for `s.help`"))

if(config.TOKEN == 'xxxxxxxxxxxxx'):
    raise RuntimeError("Please update config.py with your bot's token!")

bot.run(config.TOKEN)