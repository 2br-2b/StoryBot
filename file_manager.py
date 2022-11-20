import inspect

import os
import time
import config_manager
from pathlib import Path
import discord.file
import json
import asyncio
import asyncpg
from datetime import datetime
import uuid


class file_manager():
    
    
    async def initialize_connection(self):
        """Initializes the database connection"""
        self.db_connection = await asyncpg.connect(
            user=config_manager.get_database_user(),
            password=config_manager.get_database_password(),
            database=config_manager.get_database_name(),
            host=config_manager.get_database_host(),
            port=config_manager.get_database_port(),
        )


    def is_active_server(self, guild_id: int) -> bool:
        """Returns if a guild is currently participating in StoryBot"""
        return guild_id in self.get_all_guild_ids()
    
    
    async def getStory(self, guild_id: int, story_number = 0) -> str:
        # print(str(guild_id) + ": " + inspect.stack()[1][3])
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
        # print(str(guild_id) + ": " + inspect.stack()[1][3])
        """Appends the given line to the story and writes it to the file"""
        
        # Makes sure the bot isn't trying to append a command onto the story
        # Since this is already checked in dm_listener, this throws an error when it detects a command
        if line.startswith(config_manager.get_prefix()):
            raise RuntimeWarning("I was just told to add this to the story, but this is clearly a command:\n"+line)
        
        with open(_get_story_file_name(guild_id), "a+", encoding="utf8") as append_to:
            append_to.write(line)


    async def get_all_guild_ids(self) -> list[int]:
        """Returns a list of all the guild ids"""
        result = await self.db_connection.fetch(f"select guild_id from \"Guilds\"")
        result = [ int(r.get("guild_id")) for r in result ]
        return result
        
        
    
    async def get_current_user_id(self,  guild_id: int) -> str:
        result = (await self.db_connection.fetchrow(f"select current_user_id from \"Guilds\" where guild_id = '{guild_id}'")).get("current_user_id")
        if result == "0":
            return None
        return result
    

    async def set_current_user_id(self,  guild_id: int, user_id: int) -> str:
        """Sets the current user for a given guild"""
        if user_id == None:
            user_id = 0
        await self.db_connection.execute(f"UPDATE \"Guilds\" SET current_user_id='{user_id}' WHERE guild_id='{guild_id}'")
        return str(user_id)
        
        
    async def load_timestamp(self,  guild_id: int) -> float:
        # print(str(guild_id) + ": " + inspect.stack()[1][3])
        """Returns the timestamp if it exists. If it doesn't, it'll reset the timestamp and return the new one."""

        result = (await self.db_connection.fetchrow(f"select timestamp from \"Guilds\" where guild_id = '{guild_id}'")).get("timestamp")
        
        if result == None:
            await self.reset_timestamp(guild_id)
            return await self.load_timestamp(guild_id)
        else:
            return result.timestamp()
        

    async def reset_timestamp(self,  guild_id: int) -> None:
        # print(str(guild_id) + ": " + inspect.stack()[1][3])
        """Resets the timestamp to the current time"""
        q=datetime.now().isoformat(sep=" ", timespec="seconds")
        
        await self.db_connection.execute(f"UPDATE \"Guilds\" SET timestamp='{q}' WHERE guild_id='{guild_id}'")

@staticmethod
def _get_story_file_name(guild_id: int, story_number: int = 0) -> str:
    if story_number == 0:
        story_file_name = f"storage/{guild_id} story.txt"
    else:
        story_file_name = f"storage/archive/{guild_id} archived story {str(story_number)}.txt"
    return story_file_name