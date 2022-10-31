import os
import time
import config
import re

class file_manager():
    def __init__(self):
        file = open("story.txt", "r", encoding="utf8")
        file.close()

    def getStory(self):
        """Returns the story in the story.txt file"""
        with open("story.txt", "r", encoding="utf8") as file:
            return file.read()

    def addLine(self, line):
        """Appends the given line to the story and writes it to the file"""
        line = line.replace("\\","\n")

        # Replaces all extra spaces after line breaks
        line = re.sub(r"\n *", "\n", line) 

        # Makes sure the bot isn't trying to append a command onto the story
        # Since this is already checked in dmlistener, this throws an error when it detects a command
        if line.startswith(config.PREFIX):
            raise RuntimeWarning("I was just told to add this to the story, but this is clearly a command:\n"+line)
        
        with open("story.txt", "a", encoding="utf8") as append_to:
            append_to.write(line)

        with open("story.txt", "r", encoding="utf8") as f:
            self.story = f.read()

    @staticmethod
    def new_story(self):
        """A work in progress
        Should save the old story and restart the current story from scratch"""
        raise NotImplementedError("The `file_manager.new_story()` command is not finished yet.")
        
        with open("story.txt", "r", encoding="utf8") as f:
            old_story = f.read()

        time.sleep(0.01)

        backup_filename = file_manager.find_next_available_filename()

        with open(backup_filename, 'w') as f:
            f.write(str(old_story))

        with open('story.txt', 'w+') as f:
            f.write('')

    @staticmethod
    def find_next_available_filename() -> str:
        """This method finds the next available name for a story file and returns it"""
        i = 1
        while os.file.exists(f"story {i}.txt"):
            i += 1

        return f"story {i}.txt"
