import asyncio
import discord    
import cogs.dm_listener as dm_listener
from user_manager import user_manager
from file_manager import file_manager
from config_manager import ConfigManager
from discord.ext import commands
from discord import app_commands
import logging
import time

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

class StoryBot(commands.Bot):
    async def setup_hook(self):
        
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
    
@bot.event
async def on_guild_join(guild_joined: discord.Guild):
    await bot.file_manager.add_guild(guild_joined.id)
    print(f"added guild {guild_joined.id}")
    await dml.update_status()

@bot.event
async def on_guild_remove(guild_left: discord.Guild):
    await bot.file_manager.remove_guild(guild_left.id)
    print(f"left guild {guild_left.id}")
    await dml.update_status()
    
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        return await interaction.response.send_message(f"Command is currently on cooldown! Try again in {error.retry_after:.2f} seconds!")

    elif isinstance(error, app_commands.MissingPermissions):
        return await interaction.response.send_message("Only server moderators can do this! Make sure you have the `moderate_members` permission, then try again.")

    else:
        raise error

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

handler = logging.FileHandler(filename=f'logs/{int(time.time())} discord.log', encoding='utf-8', mode='w')

bot.tree.on_error = on_tree_error
bot.run(cmgr.get_token(), log_handler=handler)

