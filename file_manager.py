import inspect

import os
import time
import config_manager
from pathlib import Path

class file_manager():
    def __init__(self):

        if not Path("story.txt").is_file():
            print("Created story.txt")
            open("story.txt", "x").close()

    def getStory(self, guild_id: int, story_number = 0):
        print(str(guild_id) + ": " + inspect.stack()[1][3])
        """Returns the story in the story.txt file"""
        if story_number == 0:
            with open("story.txt", "r", encoding="utf8") as file:
                text = file.read() 
        else:
            with open("story " + str(story_number) + ".txt", "r", encoding="utf8") as file:
                text = file.read()
        
        if(text == ""):
            return "<Waiting for the first user to begin!>"
        else:
            return text

    def addLine(self, guild_id: int, line):
        print(str(guild_id) + ": " + inspect.stack()[1][3])
        """Appends the given line to the story and writes it to the file"""
        
        # Makes sure the bot isn't trying to append a command onto the story
        # Since this is already checked in dm_listener, this throws an error when it detects a command
        if line.startswith(config_manager.get_prefix()):
            raise RuntimeWarning("I was just told to add this to the story, but this is clearly a command:\n"+line)
        
        with open("story.txt", "a", encoding="utf8") as append_to:
            append_to.write(line)

        with open("story.txt", "r", encoding="utf8") as f:
            self.story = f.read()

    @staticmethod
    def new_story(self, guild_id: int):
        print(str(guild_id) + ": " + inspect.stack()[1][3])
        """A work in progress
        Should save the old story and restart the current story from scratch"""
        raise NotImplementedError("The `file_manager.new_story()` command is not finished yet.")
        
        with open("story.txt", "r", encoding="utf8") as f:
            old_story = f.read()

        time.sleep(0.01)

        backup_filename = file_manager.find_next_available_filename(guild_id)

        with open(backup_filename, 'w') as f:
            f.write(str(old_story))

        with open('story.txt', 'w+') as f:
            f.write('')

    @staticmethod
    def find_next_available_filename(guild_id: int) -> str:
        print(str(guild_id) + ": " + inspect.stack()[1][3])
        """This method finds the next available name for a story file and returns it"""
        i = 1
        while os.file.exists(f"story {i}.txt"):
            i += 1

        return f"story {i}.txt"

    def get_all_guild_ids(self) -> list[int]:
        # TODO: not implemented
        return [ config_manager.get_default_guild_id() ]





@staticmethod
def load_timestamp(guild_id: int, filename: str = "timestamp.txt") -> float:
    print(str(guild_id) + ": " + inspect.stack()[1][3])
    """Returns the timestamp if it exists. If it doesn't, it'll reset the timestamp and return the new one."""

    try:
        with open(filename, "r") as f:
            return float(f.read())
    except FileNotFoundError:
        print("Timestamp not found. Resetting timestamp...")
        reset_timestamp(guild_id)
        return load_timestamp(guild_id)
    except ValueError:
        reset_timestamp(guild_id)
        raise RuntimeWarning("Timestamp has been corrupted. I have reset the timestamp, but if this keeps happening, something's wrong.")

@staticmethod
def reset_timestamp(guild_id: int, filename:str = "timestamp.txt") -> float:
    print(str(guild_id) + ": " + inspect.stack()[1][3])
    """Resets the timestamp to the current time"""
    now = time.time()
    with open(filename, "w") as f:
        f.write(str(now))
    return now