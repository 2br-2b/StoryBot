import os
import time
import config

class file_manager():
    def __init__(self):
        file = open("story.txt", "r", encoding="utf8")
        self.story = file.read()
        file.close()
        
    # Returns the story in the story.txt file
    def getStory(self):
        file = open("story.txt", "r", encoding="utf8")
        self.story = file.read()
        file.close()
        return self.story

    # Appends the given line to the story and writes it to the file
    def addLine(self, line):
        with open("story.txt", "a", encoding="utf8") as append_to:
            line = line.replace("\\","\n")

            if not line.startswith(config.PREFIX):
                self.story += line
            append_to.write(line)

        with open("story.txt", "r", encodig="utf8") as f:
            self.story = f.read()

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

    # This method finds the next available name for a story file and returns it
    @staticmethod
    def find_next_available_filename() -> str:
        i = 1
        while os.file.exists(f"story {i}.txt"):
            i += 1

        return f"story {i}.txt"
