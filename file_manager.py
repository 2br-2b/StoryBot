import inspect

import os
import time
from config_manager import ConfigManager
from pathlib import Path
import discord.file
import json
import asyncio
import asyncpg
from asyncpg import exceptions as db_exceptions
from datetime import datetime
import uuid


class file_manager():
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        config_manager.set_file_manager(self)
    
    async def initialize_connection(self):
        """Initializes the database connection"""
        self.db_connection = await asyncpg.connect(
            user=await self.config_manager.get_database_user(),
            password=await self.config_manager.get_database_password(),
            database=await self.config_manager.get_database_name(),
            host=await self.config_manager.get_database_host(),
            port=await self.config_manager.get_database_port(),
        )


    async def is_active_server(self, guild_id: int) -> bool:
        """Returns if a guild is currently participating in StoryBot"""
        return guild_id in await self.get_all_guild_ids()
    
    async def add_guild(self, guild_id: int) -> None:
        if not guild_id in await self.get_all_guild_ids():
            await self.db_connection.execute(f"INSERT INTO \"Guilds\" (guild_id, timeout_days) VALUES ('{guild_id}', {await self.config_manager.get_default_timeout_days()})")
            
    async def remove_guild(self, guild_id: int) -> None:
        await self.db_connection.execute(f"delete from \"Users\" where guild_id = '{guild_id}'")
        await self.db_connection.execute(f"delete from \"Logs\" where guild_id = '{guild_id}'")
        await self.db_connection.execute(f"delete from \"Guilds\" where guild_id = '{guild_id}'")
        try:
            for i in range(0, await self.config_manager.get_max_archived_stories()):
                os.remove(_get_story_file_name(guild_id, i))
        except FileNotFoundError:
            return
                
    
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
        result = await self.db_connection.fetch(f"select guild_id from \"Guilds\"")
        result = [ int(r.get("guild_id")) for r in result ]
        return result
        
        
    
    async def get_current_user_id(self,  guild_id: int) -> str:
        """Gets the ID of the current user of a server"""
        result = (await self.db_connection.fetchrow(f"select current_user_id from \"Guilds\" where guild_id = '{guild_id}'"))
        if result == None or result == "0":
            return None
        return result.get("current_user_id")
    

    async def set_current_user_id(self,  guild_id: int, user_id: int) -> str:
        """Sets the current user for a given guild"""
        if user_id == None:
            user_id = 0
        await self.db_connection.execute(f"UPDATE \"Guilds\" SET current_user_id='{user_id}' WHERE guild_id='{guild_id}'")
        return str(user_id)
        
        
    async def load_timestamp(self,  guild_id: int) -> float:
        """Returns the timestamp if it exists. If it doesn't, it'll reset the timestamp and return the new one."""

        result = (await self.db_connection.fetchrow(f"select timestamp from \"Guilds\" where guild_id = '{guild_id}'")).get("timestamp")
        
        if result == None:
            await self.reset_timestamp(guild_id)
            return await self.load_timestamp(guild_id)
        else:
            return result.timestamp()
        

    async def reset_timestamp(self,  guild_id: int) -> None:
        """Resets the timestamp to the current time"""
        q=datetime.now().isoformat(sep=" ", timespec="seconds")
        
        await self.db_connection.execute(f"UPDATE \"Guilds\" SET timestamp='{q}' WHERE guild_id='{guild_id}'")
        
    async def get_current_turns_of_user(self, user_id: int) -> list[int]:
        """Returns all servers where it is a user's turn

        Args:
            user_id (int): the user id to check for

        Returns:
            list[int]: a list with all of the user's current turns
        """
        result = (await self.db_connection.fetch(f"select guild_id from \"Guilds\" where current_user_id = '{user_id}'"))
        result = [int(i.get("guild_id")) for i in result]
        return result
    
    async def get_user_active_guilds(self, user_id: int) -> list[int]:
        """Returns all servers where a user is active

        Args:
            user_id (int): the user id to check for

        Returns:
            list[int]: a list with all of the user's servers
        """
        result = (await self.db_connection.fetch(f"select guild_id from \"Users\" where user_id = '{user_id}'"))
        result = [int(i.get("guild_id")) for i in result]
        return result
    
    async def add_user(self, user_id: int, guild_id: int):
        try:
            if not user_id in await self.get_active_users(guild_id):
                await self.db_connection.execute(f"INSERT INTO \"Users\" (user_id, guild_id, reputation, is_admin) VALUES ('{user_id}', '{guild_id}', {await self.config_manager.get_default_reputation()}, False)")
                await self.log_action(user_id=user_id, guild_id=guild_id, action="join")
        except db_exceptions.DataError:
            print(f"Unknown guild found: {guild_id}; user_id: {user_id}")
            await self.add_guild(guild_id=guild_id)
            await self.add_user(user_id=user_id, guild_id=guild_id)
        
    
    async def remove_user(self, user_id: int, guild_id: int):
        """Removes a user from a given server"""
        await self.db_connection.execute(f"delete from \"Users\" where user_id='{user_id}' and guild_id='{guild_id}'")
        await self.log_action(user_id=user_id, guild_id=guild_id, action="leave")
    
    async def get_reputation(self, user_id: int, guild_id: int) -> int:
        """Returns the reputation of a given user in a given server"""
        return (await self.db_connection.fetchrow(f"select reputation from \"Users\" where user_id='{user_id}' and guild_id='{guild_id}'")).get("reputation")
    
    async def alter_reputation(self, user_id: int, guild_id: int, amount: int):
        """Changes a user's reputation by a given amount"""
        current_reputation=await self.get_reputation(user_id=user_id, guild_id=guild_id)
        new_reputation = current_reputation + amount
        
        if(new_reputation > await self.config_manager.get_max_reputation()):
            new_reputation = await self.config_manager.get_max_reputation()
        elif(new_reputation < 0):
            new_reputation = 0
        
        await self.db_connection.execute(f"UPDATE \"Users\" SET reputation = {new_reputation} WHERE user_id='{user_id}' AND guild_id='{guild_id}'")
        
    
    async def get_admins(self, guild_id: int) -> list[int]:
        """Returns all the admins of a given guild"""
        responses = await self.db_connection.fetch(f"select user_id from \"Users\" where guild_id='{guild_id}' and is_admin=True")
        return [int(i.get("user_id")) for i in responses]
    
    async def get_config_value(self, guild_id: int, config_value: str):
        """Returns a given config value for a server"""
        response = await self.db_connection.fetchrow(f"select {config_value} from \"Guilds\" where guild_id='{guild_id}'")
        return response.get(f"{config_value}")
    
    async def get_active_users(self, guild_id: int) -> list[int]:
        """Returns the user ids of all users in a guild"""
        responses = await self.db_connection.fetch(f"select user_id from \"Users\" where guild_id='{guild_id}'")
        return [int(i.get("user_id")) for i in responses]
    
    async def get_users_and_reputations(self, guild_id: int) -> json:
        """Returns a json-format of all the user ids and their reputations from a server

        Args:
            guild_id (int): the guild to get user ids from

        Returns:
            json: the users in a server in a {userid (str): reputation (int)} format
        """
        responses = await self.db_connection.fetch(f"select user_id, reputation from \"Users\" where guild_id='{guild_id}'")
        
        ret = {}
        for user in responses:
            ret[user.get("user_id")] = user.get("reputation")
        
        return ret
    
    async def log_action(self, user_id: int, guild_id: int, action: str) -> None:
        # Actions to be logged:
        # - Joining/leaving a story in a given server (`join`, `leave`)
        # - Adding to the story (`add`)
        # - Manually skipping (`skip`)
        # - Timing out (`timeout`)
        await self.db_connection.execute(f"INSERT INTO \"Logs\" (user_id, guild_id, action) VALUES ('{user_id}', '{guild_id}', '{action}')")
        
        
    async def get_recent_users_queue(self, guild_id: int) -> list[int]:
        user_count = len(await self.get_active_users(guild_id))
        recent_users_to_skip = user_count // 2
        results = await self.db_connection.fetch(f"select user_id from \"Logs\" where guild_id = '{guild_id}' order by timestamp DESC limit {recent_users_to_skip}")
        
        return [int(i.get("user_id")) for i in results]
        
        
        

@staticmethod
def _get_story_file_name(guild_id: int, story_number: int = 0) -> str:
    if story_number == 0:
        story_file_name = f"storage/{guild_id} story.txt"
    else:
        story_file_name = f"storage/archive/{guild_id} archived story {str(story_number)}.txt"
    return story_file_name