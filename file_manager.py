import inspect

import os
import time
import config_manager
from pathlib import Path
import discord.file
import json

class file_manager():     
    def __init__(self) -> None:
        filepath = "storage/active_servers.json"
        if not os.path.isfile(filepath):
            os.makedirs("storage/archive")
            with open(filepath, "w+") as f:
                json.dump([], f, indent=4)
        
        self.initialize_server(config_manager.get_default_guild_id())
    
    def is_active_server(self, guild_id: int) -> bool:
        """Returns if a guild is currently participating in StoryBot"""
        with open('storage/active_servers.json', 'r') as f:
            return guild_id in json.load(f)
    
    def initialize_server(self,  guild_id: int) -> None:
        if not self.is_active_server(guild_id):
            self.reset_timestamp(guild_id)
            self.addLine(guild_id, "")
            self.set_current_user_id(guild_id, None)
            
            with open('storage/active_servers.json', 'r') as f:
                active_guilds = json.load(f)
            active_guilds.append(guild_id)
            os.remove("storage/active_servers.json")
            with open('storage/active_servers.json', 'w') as f:
                json.dump(active_guilds, f, indent=4)
        
    def getStory(self, guild_id: int, story_number = 0) -> str:
        print(str(guild_id) + ": " + inspect.stack()[1][3])
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
       
    def get_story_file(self, guild_id: int, story_number = 0) -> discord.file:
        
        story_file_name = _get_story_file_name(guild_id, story_number)
        
        try:
            return discord.File(story_file_name, filename="Story.txt")
        except FileNotFoundError as e:
            if story_number == 0:
                Path(story_file_name).touch()
                return self.get_story_file(guild_id, story_number)
            else:
                raise e


    def addLine(self, guild_id: int, line):
        print(str(guild_id) + ": " + inspect.stack()[1][3])
        """Appends the given line to the story and writes it to the file"""
        
        # Makes sure the bot isn't trying to append a command onto the story
        # Since this is already checked in dm_listener, this throws an error when it detects a command
        if line.startswith(config_manager.get_prefix()):
            raise RuntimeWarning("I was just told to add this to the story, but this is clearly a command:\n"+line)
        
        with open(_get_story_file_name(guild_id), "a+", encoding="utf8") as append_to:
            append_to.write(line)


    def get_all_guild_ids(self) -> list[int]:
        with open('storage/active_servers.json', 'r') as f:
            return json.load(f)
    
    def get_current_user_id(self,  guild_id: int) -> str:
        try:
            with open(_get_current_user_file_name(guild_id)) as f:
                return f.read()
        except FileNotFoundError:
            return None

    def set_current_user_id(self,  guild_id: int, user_id: int) -> str:
        if user_id is None:
            user_id = ""
        with open(_get_current_user_file_name(guild_id), 'w+') as f:
            f.write(str(user_id))
        
        
    def load_timestamp(self,  guild_id: int) -> float:
        print(str(guild_id) + ": " + inspect.stack()[1][3])
        """Returns the timestamp if it exists. If it doesn't, it'll reset the timestamp and return the new one."""

        try:
            with open(_get_timestamp_file_name(guild_id), "r") as f:
                return float(f.read())
        except FileNotFoundError:
            print("Timestamp not found. Resetting timestamp...")
            self.reset_timestamp(guild_id)
            return self.load_timestamp(guild_id)
        except ValueError:
            self.reset_timestamp(guild_id)
            raise RuntimeWarning("Timestamp has been corrupted. I have reset the timestamp, but if this keeps happening, something's wrong.")

    def reset_timestamp(self,  guild_id: int) -> float:
        print(str(guild_id) + ": " + inspect.stack()[1][3])
        """Resets the timestamp to the current time"""
        now = time.time()
        with open(_get_timestamp_file_name(guild_id), "w+") as f:
            f.write(str(now))
        return now

    
@staticmethod
def _get_story_file_name(guild_id: int, story_number: int = 0) -> str:
    if story_number == 0:
        story_file_name = f"storage/{guild_id} story.txt"
    else:
        story_file_name = f"storage/archive/{guild_id} archived story {str(story_number)}.txt"
    return story_file_name

@staticmethod
def _get_timestamp_file_name(guild_id: int) -> str:
    return f"storage/{guild_id} timestamp.txt"

@staticmethod
def _get_current_user_file_name(guild_id: int) -> str:
    return f"storage/{guild_id} user.txt"