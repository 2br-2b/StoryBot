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

def get_timeout_days(guild_id: int) -> float:
    return config.TIMEOUT_DAYS

def get_default_reputation(guild_id: int) -> int:
    return config.DEFAULT_REPUTATION

def get_max_reputation(guild_id: int) -> int:
    return config.MAX_REPUTATION

def get_prefix() -> str:
    # TODO: phase out along while adding slash commands
    return config.PREFIX

def get_story_announcement_channels(guild_id: int) -> list(int):
    return config.STORY_CHANNELS

def get_story_output_channels(guild_id: int) -> list(int):
    return config.STORY_OUTPUT_CHANNELS

def get_send_story_as_embed(guild_id: int) -> bool:
    return config.SEND_STORY_AS_EMBED_IN_CHANNEL

def is_admin(author_id: int, guild_id: int) -> bool:
    return author_id in config.ADMIN_IDS

def get_default_user_ids() -> list(int):
    # TODO: Phase out
    return config.DEFAULT_USER_IDS

def get_embed_color() -> Color:
    return config.EMBED_COLOR

def get_amount_to_not_repeat() -> int:
    # TODO: Phase out
    return config.LAST_N_PLAYERS_NO_REPEAT