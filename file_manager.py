import os

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
        file = open("story.txt", "a", encoding="utf8")
        listOfEndings = {
            ".", "?", "!", '"', '\n', '\'', '-', '\\'
        }
        goodEnding = False
        for l in listOfEndings:
           if(line.strip().endswith(l)):
               goodEnding = True

        if not goodEnding:
            line = line.strip() + "."
        line = line.strip() + " "

        line = line.replace("\\","\n")

        if not line.lower() is 's.skip':
           self.story += line
        file.write(line)
        file.close()

        file = open("story.txt", "r", encoding="utf8")
        self.story = file.read()
        file.close()


    def new_story(self):
        with open("story.txt", "r", encoding="utf8") as f:
            old_story = f.read()

        import time
        time.sleep(0.01)

        os.remove("story.txt")

        i = 1
        while True:
            try:
                file = open(f"story {i}.txt", "r", encoding="utf8")
                file.close()
            except Exception:
                break

        with open(f'story {i}.txt', 'w') as f:
            f.write(str(old_story))

        with open('story.txt', 'w+') as f:
            f.write('')
