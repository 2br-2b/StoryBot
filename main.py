import discord

# create the necessary files if they don't exist
import config_manager

        
import cogs.dm_listener as dm_listener
from user_manager import user_manager
from file_manager import file_manager
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

class StoryBot(commands.Bot):
    async def setup_hook(self):
        
        ### Notice: if the commands are showing up two times in your server but only once in DMs, uncomment these three lines for your first run ###
        ### Then, comment them back out after this run ###
        ### This is a fix for upgrading from v1.0.1 ###
        #import config
        #bot.tree.copy_global_to(guild=discord.Object(id=config.GUILD_ID))
        #await bot.tree.sync(guild=discord.Object(id=config.GUILD_ID))
        
        await load_cogs(self, ["cogs.dm_listener"])
        await bot.tree.sync()


bot = StoryBot(config_manager.get_prefix(), help_command = None, intents=intents)

fmgr = file_manager()
umgr = user_manager(bot)
dml = dm_listener.dm_listener(fmgr, umgr, bot)

bot.file_manager = fmgr
bot.user_manager = umgr


@bot.event
async def on_ready():
    print("Bot started!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=" for `/help`"))


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


bot.run(config_manager.get_token())

