import asyncio
import discord

# create the necessary files if they don't exist


        
import cogs.dm_listener as dm_listener
from user_manager import user_manager
from file_manager import file_manager
from config_manager import ConfigManager
from discord.ext import commands

intents = discord.Intents.default()
intents.guilds = True
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
        # TODO: make this so it doesn't run every time (maybe make it a command)
        asyncio.create_task(bot.tree.sync())
        
        await bot.file_manager.initialize_connection()
        
        
cmgr = ConfigManager(None)
fmgr = file_manager(cmgr)

bot = StoryBot(cmgr.get_prefix(), help_command = None, intents=intents)


bot.config_manager = cmgr

umgr = user_manager(bot, cmgr)
dml = dm_listener.dm_listener(fmgr, umgr, bot)



bot.file_manager = fmgr
bot.user_manager = umgr


@bot.event
async def on_ready():
    print("Bot started!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=" for `/help`"))
    
@bot.event
async def on_guild_join(guild_joined: discord.Guild):
    await bot.file_manager.add_guild(guild_joined.id)
    print(f"added guild {guild_joined.id}")
    
    

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


bot.run(cmgr.get_token())

