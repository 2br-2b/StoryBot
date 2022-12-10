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

class ConfigManager():
    def __init__(self, file_manager) -> None:
        self.set_file_manager(file_manager)

    def set_file_manager(self, file_manager) -> None:
        self.file_manager = file_manager

    def get_token(self) -> str:
        if(config.TOKEN == 'xxxxxxxxxxxxx'):
            raise RuntimeError("Please update config.py with your bot's token!")
        return config.TOKEN

    async def get_default_timeout_days(self) -> float:
        return config.TIMEOUT_DAYS

    async def get_timeout_days(self, guild_id: int) -> float:
        return int(await self.file_manager.get_config_value(guild_id, "timeout_days"))

    async def get_default_reputation(self) -> int:
        return config.DEFAULT_REPUTATION

    async def get_max_reputation(self) -> int:
        return config.MAX_REPUTATION

    def get_prefix(self) -> str:
        # TODO: phase out along while adding slash commands
        return config.PREFIX

    async def get_story_announcement_channel(self, guild_id: int) -> int:
        channel_id_string = await self.file_manager.get_config_value(guild_id, "story_announcement_channel")
        if channel_id_string != None:
            return int(channel_id_string)
        else:
            return None

    async def get_story_output_channel(self, guild_id: int) -> int:
        channel_id_string = await self.file_manager.get_config_value(guild_id, "story_output_channel")
        if channel_id_string != None:
            return int(channel_id_string)
        else:
            return None

    async def is_admin(self, author_id: int, guild_id: int) -> bool:
        return author_id in await self.file_manager.get_admins(guild_id)

    async def get_embed_color(self) -> Color:
        return config.EMBED_COLOR

    async def is_debug_mode(self) -> bool:
        try:
            return config.DEBUG_MODE
        except AttributeError:
            return False
        
    async def get_database_user(self) -> str:
        return config.DATABASE_USER

    async def get_database_password(self) -> str:
        return config.DATABASE_PASSWORD

    async def get_database_name(self) -> str:
        return config.DATABASE_DB_NAME

    async def get_database_host(self) -> str:
        return config.DATABASE_HOST

    async def get_database_port(self) -> str:
        return config.DATABASE_PORT
    
    async def get_max_archived_stories(self) -> int:
        try:
            return config.MAX_ARCHIVED_STORIES
        except AttributeError:
            return 10