import os
from config_manager import ConfigManager
from pathlib import Path
import discord.file
import json
import asyncpg
from asyncpg import exceptions as db_exceptions
from datetime import datetime
import storybot_exceptions
from better_profanity import profanity

class file_manager():
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        config_manager.set_file_manager(self)
        self.OPEN_DB_CONNECTIONS = 0
        self.next_connection_to_use = 0
        profanity.load_censor_words()
    
    async def initialize_connection(self):
        """Initializes the database connection pool"""
        
        user=await self.config_manager.get_database_user()
        password=await self.config_manager.get_database_password()
        database=await self.config_manager.get_database_name()
        host=await self.config_manager.get_database_host()
        port=await self.config_manager.get_database_port()
        
        db_pool = await asyncpg.create_pool(
            user=user,
            password=password,
            database=database,
            host=host,
            port=port,
            min_size = await self.config_manager.get_min_db_connection_count(),
            max_size = await self.config_manager.get_max_db_connection_count(),
        )
        
        self.database_pool = db_pool
        
    def _get_db_connection_pool(self) -> asyncpg.Pool:
        """Returns a database pool on which execute, etc. can be called"""
        return self.database_pool


    async def is_active_server(self, guild_id: int) -> bool:
        """Returns if a guild is currently participating in StoryBot"""
        return guild_id in await self.get_all_guild_ids()
    
    async def add_guild(self, guild_id: int) -> None:
        if not guild_id in await self.get_all_guild_ids():
            await self._get_db_connection_pool().execute(f"INSERT INTO \"Guilds\" (guild_id, timeout_days) VALUES ('{guild_id}', {await self.config_manager.get_default_timeout_days()})")
            
    async def remove_guild(self, guild_id: int) -> None:
        print (f"leaving guild {guild_id}")
        pool = self._get_db_connection_pool()
        
        await pool.execute(f"delete from \"Users\" where guild_id = '{guild_id}'")
        await pool.execute(f"delete from \"Logs\" where guild_id = '{guild_id}'")
        await pool.execute(f"delete from \"Guilds\" where guild_id = '{guild_id}'")
        try:
            for i in range(0, await self.config_manager.get_max_archived_stories(guild_id=guild_id)):
                os.remove(_get_story_file_name(guild_id, i))
        except FileNotFoundError:
            return
        print (f"left guild {guild_id}")
    
    async def getStory(self, guild_id: int, story_number = 0) -> str:
        """Returns the story in the story.txt file"""

        story_file_name = _get_story_file_name(guild_id, story_number)

        try:
            with open(story_file_name, "r", encoding="utf8") as file:
                text = file.read() 
        except FileNotFoundError as e:
            if story_number == 0:
                Path(story_file_name).touch()
                return self.getStory(guild_id, story_number)
            else:
                raise e
        
        
        if(text == ""):
            return "<Waiting for the first user to begin!>"
        else:
            return text
       
    async def get_story_file(self, guild_id: int, story_number = 0) -> discord.file:
        story_file_name = _get_story_file_name(guild_id, story_number)
        try:
            return discord.File(story_file_name, filename="Story.txt")
        except FileNotFoundError as e:
            if story_number == 0:
                Path(story_file_name).touch()
                return await self.get_story_file(guild_id, story_number)
            else:
                raise e
        

    async def addLine(self, guild_id: int, line):
        """Appends the given line to the story and writes it to the file"""
        
        # Makes sure the bot isn't trying to append a command onto the story
        # Since this is already checked in dm_listener, this throws an error when it detects a command
        if line.startswith(self.config_manager.get_prefix()):
            raise RuntimeWarning("I was just told to add this to the story, but this is clearly a command:\n"+line)
        
        with open(_get_story_file_name(guild_id), "a+", encoding="utf8") as append_to:
            append_to.write(line)


    async def get_all_guild_ids(self) -> list[int]:
        """Returns a list of all the guild ids"""
        result = await self._get_db_connection_pool().fetch(f"select guild_id from \"Guilds\"")
        result = [ int(r.get("guild_id")) for r in result ]
        return result
        
        
    
    async def get_current_user_id(self,  guild_id: int) -> str:
        """Gets the ID of the current user of a server"""
        result = (await self._get_db_connection_pool().fetchrow(f"select current_user_id from \"Guilds\" where guild_id = '{guild_id}'"))
        if result == None or result == "0":
            return None
        return result.get("current_user_id")
    

    async def set_current_user_id(self,  guild_id: int, user_id: int) -> str:
        """Sets the current user for a given guild"""
        if user_id == None:
            user_id = 0
        await self._get_db_connection_pool().execute(f"UPDATE \"Guilds\" SET current_user_id='{user_id}' WHERE guild_id='{guild_id}'")
        return str(user_id)
        
        
    async def load_timestamp(self,  guild_id: int) -> float:
        """Returns the timestamp if it exists. If it doesn't, it'll reset the timestamp and return the new one."""

        result = (await self._get_db_connection_pool().fetchrow(f"select timestamp from \"Guilds\" where guild_id = '{guild_id}'")).get("timestamp")
        
        if result == None:
            await self.reset_timestamp(guild_id)
            return await self.load_timestamp(guild_id)
        else:
            return result.timestamp()
        

    async def reset_timestamp(self,  guild_id: int) -> None:
        """Resets the timestamp to the current time"""
        q=datetime.now().isoformat(sep=" ", timespec="seconds")
        
        await self._get_db_connection_pool().execute(f"UPDATE \"Guilds\" SET timestamp='{q}' WHERE guild_id='{guild_id}'")
        await self.set_notified(guild_id, False)
        
    async def get_current_turns_of_user(self, user_id: int) -> list[int]:
        """Returns all servers where it is a user's turn

        Args:
            user_id (int): the user id to check for

        Returns:
            list[int]: a list with all of the user's current turns
        """
        result = (await self._get_db_connection_pool().fetch(f"select guild_id from \"Guilds\" where current_user_id = '{user_id}'"))
        result = [int(i.get("guild_id")) for i in result]
        return result
    
    async def get_user_active_guilds(self, user_id: int) -> list[int]:
        """Returns all servers where a user is active

        Args:
            user_id (int): the user id to check for

        Returns:
            list[int]: a list with all of the user's servers
        """
        result = (await self._get_db_connection_pool().fetch(f"select guild_id from \"Users\" where user_id = '{user_id}'"))
        result = [int(i.get("guild_id")) for i in result]
        return result
    
    async def add_user(self, user_id: int, guild_id: int):
        try:
            if not user_id in await self.get_active_users(guild_id):
                if await self.user_is_banned(guild_id=guild_id, user_id=user_id):
                    raise storybot_exceptions.UserIsBannedException(f"{user_id} is banned in {guild_id}")
                
                await self._get_db_connection_pool().execute(f"INSERT INTO \"Users\" (user_id, guild_id, reputation) VALUES ('{user_id}', '{guild_id}', {await self.config_manager.get_default_reputation()})")
                await self.log_action(user_id=user_id, guild_id=guild_id, XSS_WARNING_action="join")
        except asyncpg.exceptions.ForeignKeyViolationError:
            print(f"Unknown guild found: {guild_id}; user_id: {user_id}")
            await self.add_guild(guild_id=guild_id)
            await self.add_user(user_id=user_id, guild_id=guild_id)
        
    async def user_is_banned(self, guild_id: int, user_id: int) -> bool:
        """Returns whether a user is banned in a given guild

        Args:
            guild_id (int): the guild to check
            user_id (int): the user to check

        Returns:
            bool: True if the user is banned, False if not
        """
        response = await self._get_db_connection_pool().fetchrow(f"SELECT ban_id from \"Bans\" where user_id = '{user_id}' and guild_id = '{guild_id}'")
        return response != None
        
    async def ban_user(self, guild_id: int, user_id: int):
        """Bans a user from a given server and kicks them"""
        await self._get_db_connection_pool().execute(f"INSERT INTO \"Bans\" (user_id, guild_id) VALUES ('{user_id}', '{guild_id}')")
        await self.log_action(user_id=user_id, guild_id=guild_id, XSS_WARNING_action="ban")
        await self.remove_user(user_id=user_id, guild_id=guild_id)
    
    async def remove_user(self, user_id: int, guild_id: int):
        """Removes a user from a given server"""
        await self._get_db_connection_pool().execute(f"delete from \"Users\" where user_id='{user_id}' and guild_id='{guild_id}'")
        await self.log_action(user_id=user_id, guild_id=guild_id, XSS_WARNING_action="leave")
    
    async def unban_user(self, guild_id: int, user_id: int):
        """Unbans a user from a given server"""
        await self._get_db_connection_pool().execute(f"DELETE FROM \"Bans\" WHERE user_id = '{user_id}' AND guild_id = '{guild_id}'")
        await self.log_action(user_id=user_id, guild_id=guild_id, XSS_WARNING_action="unban")
    
    async def get_reputation(self, user_id: int, guild_id: int) -> int:
        """Returns the reputation of a given user in a given server"""
        return (await self._get_db_connection_pool().fetchrow(f"select reputation from \"Users\" where user_id='{user_id}' and guild_id='{guild_id}'")).get("reputation")
    
    async def alter_reputation(self, user_id: int, guild_id: int, amount: int):
        """Changes a user's reputation by a given amount"""
        current_reputation=await self.get_reputation(user_id=user_id, guild_id=guild_id)
        new_reputation = current_reputation + amount
        
        if(new_reputation > await self.config_manager.get_max_reputation()):
            new_reputation = await self.config_manager.get_max_reputation()
        elif(new_reputation < 0):
            new_reputation = 0
        
        await self._get_db_connection_pool().execute(f"UPDATE \"Users\" SET reputation = {new_reputation} WHERE user_id='{user_id}' AND guild_id='{guild_id}'")
    
    async def get_config_value(self, guild_id: int, XSS_WARNING_config_value: str):
        """Returns a given config value for a server"""
        response = await self._get_db_connection_pool().fetchrow(f"select {XSS_WARNING_config_value} from \"Guilds\" where guild_id='{guild_id}'")
        return response.get(f"{XSS_WARNING_config_value}")
    
    async def set_config_value(self, guild_id: int, XSS_WARNING_config_name: str, new_value: int) -> None:
        """Changes a given config value for a server. XSS_WARNING is in caps to emphasize that the user **should not** be given control of this, as it could lead to SQL injection attacks"""
        
        
        await self._get_db_connection_pool().execute(f"UPDATE \"Guilds\" SET {XSS_WARNING_config_name}={new_value} WHERE guild_id='{guild_id}'")
        
        
    async def get_active_users(self, guild_id: int) -> list[int]:
        """Returns the user ids of all users in a guild"""
        responses = await self._get_db_connection_pool().fetch(f"select user_id from \"Users\" where guild_id='{guild_id}'")
        return [int(i.get("user_id")) for i in responses]
    
    async def get_users_and_reputations(self, guild_id: int) -> json:
        """Returns a json-format of all the user ids and their reputations from a server

        Args:
            guild_id (int): the guild to get user ids from

        Returns:
            json: the users in a server in a {userid (str): reputation (int)} format
        """
        responses = await self._get_db_connection_pool().fetch(f"select user_id, reputation from \"Users\" where guild_id='{guild_id}'")
        
        ret = {}
        for user in responses:
            ret[user.get("user_id")] = user.get("reputation")
        
        return ret
    
    async def log_action(self, user_id: int, guild_id: int, XSS_WARNING_action: str, sent_message_id: int = None, characters_sent: int = None) -> None:
        # Actions to be logged:
        # - Joining/leaving a story in a given server (`join`, `leave`)
        # - Adding to the story (`add`)
        # - Manually skipping (`skip`)
        # - Timing out (`timeout`)
        
        if sent_message_id == None:
            sent_message_id = "NULL"
        else:
            sent_message_id = f"'{sent_message_id}'"
            
        if characters_sent == None:
            characters_sent = "NULL"
        
        await self._get_db_connection_pool().execute(f"INSERT INTO \"Logs\" (user_id, guild_id, action, sent_message_id, characters_in_chunk) VALUES ('{user_id}', '{guild_id}', '{XSS_WARNING_action}', {sent_message_id}, {characters_sent})")
        
    async def get_recent_users_queue(self, guild_id: int) -> list[int]:
        user_count = len(await self.get_active_users(guild_id))
        recent_users_to_skip = user_count // 2
        results = await self._get_db_connection_pool().fetch(f"select user_id from \"Logs\" where guild_id = '{guild_id}' order by timestamp DESC limit {recent_users_to_skip}")
        
        return [int(i.get("user_id")) for i in results]
    
    
    async def set_notified(self, guild_id: int, notified: bool) -> None:
        await self._get_db_connection_pool().execute(f"UPDATE \"Guilds\" SET notified={notified} WHERE guild_id='{guild_id}'")
        
    async def get_notified(self, guild_id: int) -> bool:
        result = await self._get_db_connection_pool().fetch(f"SELECT notified FROM \"Guilds\" WHERE guild_id='{guild_id}'")
        return result[0].get("notified")
    
    
    async def get_archived_story_count(self, guild_id: int) -> int:
        i = 1
        while i <= await self.config_manager.get_max_archived_stories(guild_id=guild_id):
            if not os.path.isfile(_get_story_file_name(guild_id, i)):
                break
            i += 1
            
        return i - 1
    
    
    async def new_story(self, guild_id: int, forced: bool = False) -> None:
        existing_count = await self.get_archived_story_count(guild_id)
        if existing_count >= await self.config_manager.get_max_archived_stories(guild_id=guild_id):
            if not forced: raise storybot_exceptions.TooManyArchivedStoriesException(f"Guild id {guild_id} already has the maximum number of stories allotted!")
            
            # Reduce all the story counts by 1
            for i in range(2, existing_count + 1):
                os.replace(_get_story_file_name(guild_id, i), _get_story_file_name(guild_id, i - 1))
            existing_count -= 1
            
        # Add the current story as the last story
        try:
            os.replace(_get_story_file_name(guild_id), _get_story_file_name(guild_id, existing_count + 1))
        except FileNotFoundError:
            pass
        Path(_get_story_file_name(guild_id)).touch()
        
    def get_active_connection_count(self) -> int:
        return self._get_db_connection_pool().get_size()
    
    async def filter_profanity(self, content: str) -> str:
        """Filters out profanity from the given string. If there is too much profanity or the content of the message is too bad, it will raise a TooMuchProfanityError"""
        
        return profanity.censor(content, "\*")
        
        
        

@staticmethod
def _get_story_file_name(guild_id: int, story_number: int = 0) -> str:
    if story_number == 0:
        story_file_name = f"storage/{guild_id} story.txt"
    else:
        story_file_name = f"storage/archive/{guild_id} archived story {str(story_number)}.txt"
    return story_file_name