import os
import time
import config
import re

class file_manager():
    def __init__(self):
        file = open("story.txt", "r", encoding="utf8")
        file.close()
        
    # Returns the story in the story.txt file
    def getStory(self):
        with open("story.txt", "r", encoding="utf8") as file:
            return file.read()

    # Appends the given line to the story and writes it to the file
    def addLine(self, line):
        line = file_manager.fix_line_ending(line).replace("\\","\n")

        # Replaces all extra spaces after line breaks
        line = re.sub(r"\n *", "\n", line) 

        # Makes sure the user isn't sending a command before writing the story
        # Since this is already checked in dmlistener, this throws an error when it starts with a command
        if line.startswith(config.PREFIX):
            raise RuntimeWarning("I was just told to add this to the story, but this is clearly a command:"+line)
        
        with open("story.txt", "a", encoding="utf8") as append_to:
            append_to.write(line)

    # A work in progress
    # Should save the old story and restart the current story from scratch
    @staticmethod
    def new_story(self):
        with open("story.txt", "r", encoding="utf8") as f:
            old_story = f.read()

        time.sleep(0.01)

        backup_filename = file_manager.find_next_available_filename()

        with open(backup_filename, 'w') as f:
            f.write(str(old_story))

        with open('story.txt', 'w+') as f:
            f.write('')

    # Sometimes, people entering submissions don't include periods at the end of their submission.
    # In order to fix that, this method automatically ends a given string with a period if the text does not already have some character indicating the end of a sentence.
    @staticmethod
    def fix_line_ending(line: str) -> str:
        good_endings = (
            ".", "?", "!", '"', "\'", "-", "\\"
        )
        stripped_line = line.strip()
        has_good_ending = any(stripped_line.endswith(p) for p in good_endings)

        if not has_good_ending:
            return stripped_line + ". "
        return stripped_line + " "

    # This method finds the next available name for a story file and returns it
    @staticmethod
    def find_next_available_filename() -> str:
        i = 1
        while os.file.exists(f"story {i}.txt"):
            i += 1

        return f"story {i}.txt"
