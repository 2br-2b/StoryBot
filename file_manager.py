import os
import time
import config

class file_manager():
    def __init__(self, bot):
        file = open("story.txt", "r", encoding="utf8")
        self.story = file.read()
        file.close()
        self.bot = bot
        
    
    def getStory(self):
        file = open("story.txt", "r", encoding="utf8")
        self.story = file.read()
        file.close()
        return self.story

    def addLine(self, line):
        with open("story.txt", "a", encoding="utf8") as append_to:
            line = file_manager.fix_line_ending(line).replace("\\","\n")

            if not line.startswith(config.PREFIX):
                self.story += line
            append_to.write(line)

        with open("story.txt", "r", encodig="utf8") as f:
            self.story = f.read()

    def new_story(self):
        with open("story.txt", "r", encoding="utf8") as f:
            old_story = f.read()

        time.sleep(0.01)

        backup_filename = file_manager.find_next_available_filename()

        with open(backup_filename, 'w') as f:
            f.write(str(old_story))

        with open('story.txt', 'w+') as f:
            f.write('')

    @staticmethod
    def fix_line_ending(line: str) -> str:
        good_endings = (
            ".", "?", "!", '"', "\'", "-", "\\"
        )
        stripped_line = line.strip()
        has_good_ending = any(stripped_line.endswith(p) for p in good_endings)

        if not has_good_ending:
            return stripped_line + "."
        return stripped_line + " "

    @staticmethod
    def find_next_available_filename() -> str:
        i = 1
        while os.file.exists(f"story {i}.txt"):
            i += 1

        return f"story {i}.txt"
