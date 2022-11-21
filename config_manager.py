import inspect

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
        
        
from discord import Color

def get_token() -> str:
    if(config.TOKEN == 'xxxxxxxxxxxxx'):
        raise RuntimeError("Please update config.py with your bot's token!")
    return config.TOKEN

def get_default_timeout_days() -> float:
    return config.TIMEOUT_DAYS

def get_timeout_days(guild_id: int) -> float:
    return config.TIMEOUT_DAYS

def get_default_reputation() -> int:
    return config.DEFAULT_REPUTATION

def get_max_reputation() -> int:
    return config.MAX_REPUTATION

def get_prefix() -> str:
    # TODO: phase out along while adding slash commands
    return config.PREFIX

def get_story_announcement_channels(guild_id: int) -> list[int]:
    return config.STORY_CHANNELS

def get_story_output_channels(guild_id: int) -> list[int]:
    return config.STORY_OUTPUT_CHANNELS

def is_admin(author_id: int, guild_id: int) -> bool:
    return author_id in config.ADMIN_IDS

def get_default_user_ids() -> list[int]:
    # TODO: Phase out
    return config.DEFAULT_USER_IDS

def get_embed_color() -> Color:
    return config.EMBED_COLOR

def get_amount_to_not_repeat() -> int:
    # TODO: Phase out
    return config.LAST_N_PLAYERS_NO_REPEAT

def get_default_guild_id() -> int:
    return config.GUILD_ID

def is_debug_mode() -> bool:
    try:
        return config.DEBUG_MODE
    except AttributeError:
        return False
    
        
def get_database_user() -> str:
    return config.DATABASE_USER

def get_database_password() -> str:
    return config.DATABASE_PASSWORD

def get_database_name() -> str:
    return config.DATABASE_DB_NAME

def get_database_host() -> str:
    return config.DATABASE_HOST

def get_database_port() -> str:
    return config.DATABASE_PORT