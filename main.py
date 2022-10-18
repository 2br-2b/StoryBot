import discord
import config
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
    print("Started!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=" for `s.help`"))

bot.run(config.TOKEN)