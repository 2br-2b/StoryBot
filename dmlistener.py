import discord
import math
import asyncio
import pathlib
import time
import os
import collections
from discord.ext import tasks, commands
import re
from discord import Embed

import config
import file_manager

# Listens for DMs to add to the story
class dmlistener(commands.Cog):
    def __init__(self, file_manager, user_manager, bot):
        self.file_manager = file_manager
        self.user_manager = user_manager
        
        # Keeps track of the current user's id
        self.current_user = int(user_manager.get_current_user())
        
        self.bot = bot
        self.messageNotSent = False
        # self.timeout_checker.start()
        self.last_checked_user = self.current_user

        # The timestamp keeps track of when the last user was notified, so that even if the bot goes down, it still knows how much longer the current user has to continue the story
        self.timestamp = dmlistener.load_timestamp("timestamp.txt")
        self._notif_line_cont = False
        
        self.CHARACTERS_TO_SHOW = 4096

    async def dm_current_user(self, message, file = None, embed = None):
        """Sends the given message to the current user"""
        
        await (await (await self.bot.fetch_user(int(self.user_manager.get_current_user()))).create_dm()).send(message, embed=embed, file = file)
        if self._notif_line_cont:
            self._notif_line_cont = False
            await self.dm_current_user("**Please pick up the writing in the middle of the last sentence.**")
            

    async def notify_people(self):
        """Notifies the current user that it's their turn to add to the story"""
        
        file = discord.File("story.txt", filename="story.txt")
        await self.dm_current_user("""Your turn.  Respond with a DM to continue the story!  Use a \ to create a line break.
            
            **MAKE SURE THE BOT IS ONLINE BEFORE RESPONDING!**  You will get a confirmation response if your story is received.
            
            Here is the story so far:""", file = file, embed = create_embed(content=self.lastChars(self.file_manager.getStory()), author_name=None, author_icon_url=None))
        
        
        
        # Send a message in the story chanel
        for channel in config.STORY_CHANNELS:
            await self.bot.get_channel(channel).send("It's now {0}'s turn!".format((await self.bot.fetch_user(int(self.user_manager.get_current_user()))).name))

    @commands.command()
    async def story(self, ctx, *parameters):
        """Sends a reply with the requested story
        If there is a number, the given story number will be returned"""
        
        # TODO: use file_manager.py here
        
        try:
            if parameters[-1].isdigit():
                print('Story requested. Correct digit found!')
                file = discord.File("story {0}.txt".format(int(parameters[-1])), filename="story {0}.txt".format(int(parameters[-1])))
                await self.reply_to_message(ctx.message, 'Here is story {0}:'.format(int(parameters[-1])), file = file)
            else:
                print('Story requested. No digit found!')
                raise Exception('')
        except:
            file = discord.File("story.txt", filename="story.txt")
            await self.reply_to_message(ctx.message, ""+self.lastChars(self.file_manager.getStory())+"", file = file)

    @commands.is_owner()
    @commands.command()
    async def push(self, ctx):
        """Syncs the story with the old git repo
        Will need to be removed"""
        
        return
        import os, time
        os.system("git commit -am \"{0}\"".format(time.time()))
        os.system("git pull")
        os.system("git push")
        await self.reply_to_message(ctx.message, "oki swine it done")

    @commands.command()
    async def turn(self, ctx):
        """Sends a message with the current user's name"""
        current_user = await self.bot.fetch_user(int(self.user_manager.get_current_user()))
        
        #ctx.message.guild.get_member(int(self.user_manager.get_current_user()))
        await self.reply_to_message(ctx.message, content="", author=current_user)

    @commands.command()
    async def help(self, ctx):
        """The help command"""
        
        await self.reply_to_message(ctx.message, 
            """This bot is a story bot.  One user will write a part of the story (anywhere from a sentence or two to a couple of paragraphs - your choice!), then another, and so on until the story is complete!
            
    `""" + config.PREFIX + "add` adds you to the authors, while `"+config.PREFIX + """remove` removes you
    `""" + config.PREFIX + """story` displays the story so far - put a number afterwards to see a past story
    `""" + config.PREFIX + "turn` displays whose turn it is")

    @commands.command()
    async def skip(self, ctx):
        """Skips the current user"""
        
        if str(ctx.author.id) != self.user_manager.get_current_user() and not ctx.author.id in config.ADMIN_IDS:
            await self.reply_to_message(ctx.message, "It's not your turn!")
            return
        await self.reply_to_message(ctx.message, "Skipping :(")
        self.current_user = self.user_manager.set_random_weighted_user()

        await self.notify_people()
        await self.wait_and_check()

    @commands.command()
    async def notify(self, ctx):
        """The command to notify users that it's their turn"""
        
        await self.notify_people()

    @commands.is_owner()
    @commands.command()
    async def list_users(self, ctx):
        """Lists the users working on the story"""
        
        print("\nList of users:\n" + self.user_manager.get_weighted_list())

    @commands.Cog.listener()
    async def on_message(self, message):
        """Checks if the message should be added the story, and if it is, appends it"""
        
        if self.messageNotSent:
            file = discord.File("story.txt", filename="story.txt")
            await self.notify_people()
            self.messageNotSent = False

        if message.guild is None:
            if self.user_manager.get_current_user() == str(message.author.id):
                if message.content.startswith(config.PREFIX):
                    return
                
                # Add the given line to the story file
                self.file_manager.addLine(self.format_story_addition(message.content))
                
                # Mirror the messages to a Discord channel
                for channel in config.STORY_OUTPUT_CHANNELS:
                    await self.bot.get_channel(channel).send(self.format_story_addition(message.content))
                
                self.user_manager.boost_user(self.current_user)
                self.current_user = self.user_manager.set_random_weighted_user()
                await self.reply_to_message(message, "Got it!  Thanks!")

                await self.notify_people()
                await self.wait_and_check()

    def pieMethod(self, story):
        """The all-powerful pieMethod
        Splits the story into a list of strings if it is too long"""
        
        if len(story) >= self.CHARACTERS_TO_SHOW:
            split = list()
            for i in range(math.ceil(len(story) / self.CHARACTERS_TO_SHOW)):
                if i == math.ceil(len(story) / self.CHARACTERS_TO_SHOW):
                    split.append(story[i:len(story) -1])
                else:
                    split.append(story[i:i+self.CHARACTERS_TO_SHOW])
            return split
        else:
            return [story]

    def lastChars(self, story):
        """Returns the last self.CHARACTERS_TO_SHOW characters of the story"""
        
        if(len(story) > self.CHARACTERS_TO_SHOW):
            return story[len(story) - self.CHARACTERS_TO_SHOW:len(story) -1]
        else:
            return story

    async def wait_and_check(self):
        """Should wait for the specified amount of days, then skip the current user's turn"""
        
        return
        def check(message):
            return str(message.author.id) == self.user_manager.get_current_user()

        try:
            message2, user = await self.bot.wait_for('on_message', timeout = 60*60*24*config.TIMEOUT_DAYS, check = check)
        except asyncio.TimeoutError:
            await timeout_happened()

    async def timeout_happened(self):
        """Skips the current user's turn if they don't respond in the specified amount of time"""
        
        print('about to dm '+str(self.current_user) + ' that they have been skipped due to taking too long') 
        try:
            await self.dm_current_user('You took too long!  You\'ll have a chance to add to the story later - don\'t worry!')
            print('skip dm to '+str(self.current_user)+' successful.  About to unboost...')
        except:
            print('failed to DM '+str(self.current_user)+'.  Moving on...')
        self.user_manager.unboost_user(self.current_user)
        print('unboosted '+str(self.current_user)+'.  About to change current user......') 
        self.current_user = self.user_manager.set_random_weighted_user()
        print('done changing user to '+str(self.current_user)+'. About to notify people...')
        await self.notify_people()

        self.last_checked_user = self.current_user
        self.timestamp = time.time()
        os.remove('timestamp.txt')
        with open('timestamp.txt', 'w') as f:
            f.write(str(self.timestamp))

    @tasks.loop(seconds=60 * 60) # Check back every hour
    async def timeout_checker(self):
        """SHOULD skip the current user's turn if they don't respond in the specified amount of time"""
        
        if self.last_checked_user is self.current_user: #still the same person
            if time.time() - self.timestamp >= 60 * 60 * 24 * config.TIMEOUT_DAYS: # if the time is over the allotted time
                print('about to timeout for '+str(self.current_user))
                await self.timeout_happened()
                print('timeout happened. New user is '+str(self.current_user))

        else: #new person
            self.last_checked_user = self.current_user
            self.timestamp = time.time()
            os.remove('timestamp.txt')
            with open('timestamp.txt', 'w') as f:
                f.write(str(self.timestamp))
        
        print('checked: {0} seconds at {1}'.format(time.time() - self.timestamp, time.time()))


    @commands.Cog.listener()
    async def on_ready(self):
        if not self.timeout_checker.running:
            self.timeout_checker.start()

    def cog_unload(self):
        self.timeout_checker.cancel()

    @commands.command()
    async def add(self, ctx):
        """Adds a user to the list of participants"""
        
        self.user_manager.add_user(ctx.author.id)
        await self.reply_to_message(ctx.message, "Done!")

    @commands.command()
    async def remove(self, ctx):
        """Removes a user from the list of participants"""
        
        self.user_manager.remove_user(ctx.author.id)
        await self.reply_to_message(ctx.message, "Done!")

    @commands.is_owner()
    @commands.command()
    async def newstory(self, ctx):
        """Should be used at the end of a story to create a new story"""
        
        #TODO: finish it
        await self.reply_to_message(ctx.message, "This command isn't ready yet!")
        #file_manager.new_story()
        #await self.reply_to_message(ctx.message, "Done!")

    @commands.is_owner()
    @commands.command(aliases = ['rep'])
    async def reputation(self, ctx, mentn : discord.Member = None):
        """Gives the reputation of a current user"""
        
        if mentn == None:
            ID = int(ctx.author.id)
        else:
            ID = int(mentn.id)

        print('listing reputations:\n'+collections.Counter(self.user_manager.get_weighted_list()))

        await self.reply_to_message(ctx.message, collections.Counter(self.user_manager.get_weighted_list())[ID])

    @commands.is_owner()
    @commands.command(aliases = ['lsrep', 'listrep'])
    async def listreputation(self, ctx):
        """Lists all users' reputations along with their names"""
        s = ''
        for item in collections.Counter(self.user_manager.get_weighted_list()).keys():
            s += (await self.bot.fetch_user(item)).name + ': ' + str(collections.Counter(self.user_manager.get_weighted_list())[item]) + '\n'
        await self.reply_to_message(ctx.message, s)

    @commands.is_owner()
    @commands.command(aliases = [])
    async def boost(self, ctx, mentn : discord.Member = None):
        """Boosts a user's reputation"""
        return
        if mentn == None:
            ID = int(ctx.author.id)
        else:
            ID = int(mentn.id)

        self.user_manager.boost_user(id)
            
        await self.reply_to_message(ctx.message, f"Boosted <@!{ID}>!")

    @commands.is_owner()
    @commands.command(aliases = [])
    async def unboost(self, ctx, mentn : discord.Member = None):
        """Unboosts a user's reputation"""
        return
        if mentn == None:
            ID = int(ctx.author.id)
        else:
            ID = int(mentn.id)

        self.user_manager.boost_user(id)
            
        await self.reply_to_message(ctx.message, f"Unboosted <@!{ID}>!")

    @staticmethod
    def load_timestamp(filename: str) -> float:
        """Returns the timestamp if it exists. If it doesn't, it'll reset the timestamp and return the new one."""
        full_path = pathlib.Path(__file__).parent / filename
        if not os.path.exists(full_path):
            return dmlistener.reset_timestamp(full_path)

        with open(full_path, "r") as f:
            try:
                return float(f.read())
            except ValueError:
                dmlistener.reset_timestamp(full_path)
                raise RuntimeWarning("Timestamp has been corrupted. I have reset the timestamp, but if this keeps happening, something's wrong.")

    @staticmethod
    def reset_timestamp(path: pathlib.Path) -> float:
        """Resets the timestamp to the current time"""
        now = time.time()
        with open(path, "w") as f:
            f.write(str(now))
        return now

    def format_story_addition(self, line:str) -> str:
        if(line.startswith(config.PREFIX)):
            return None
        
        line = self.fix_line_ending(line)
        
        line = line.replace("\\","\n")

        # Replaces all extra spaces after line breaks
        line = re.sub(r"\n *", "\n", line) 
        
        return line


    def fix_line_ending(self, line: str) -> str:
        """Determines if a line ends with an ellipses and either:
        - removes the ellipses if it exists or
        - adds a period if it doesn't have an ellipses and if a period is needed
        
        It also strips any extra spaces at the end of a line and replaces them with a single space"""
        
        if ends_with_continuation_string(line):
            self._notif_line_cont = True
            return trim_ellipses(line)
        else:
            return add_period_if_missing(line)
        
        
    async def reply_to_message(self, message: discord.Message, content: str, file: discord.File = None, author: discord.User = None, title: str = None):
        """Replies the given message

        Args:
            message (discord.abc.Messageable): the message or ctx to reply to
            content (str): the content to reply to
            file (discord.File): the file to embed (if one is needed)
            author (str): the user to display on the embed
        """
        
        if author is None:
            author = message.author
        
        
        
        await message.reply(embed = create_embed(content=content, title=title, author_name=author.name, author_icon_url=author.display_avatar.url), file = file, mention_author = False)


def create_embed(content=None, color=config.EMBED_COLOR, title=None, author_name=None, author_icon_url=None) -> discord.Embed:
    """Creates an embed with the given parameters. All values have defaults if not given."""
    emb = discord.Embed(description=content, color=color, title=title)
    emb.set_author(name=author_name, icon_url=author_icon_url)
    
    return emb

continuation_strings = ["...", "…"]

def trim_ellipses(line: str) -> str:
    """This will remove from the beginning and end of the line:
    - Any count of three or more `.`s (to fix anyone adding lots of extra dots)
    - Any number of `…`s (to account for mobile users)
    - Any whitespace (to account for someone typing spaces before or after an ellipses)
    - Any combination of the above
    
    It will then add a single space at the end of the line."""

    # Does the regex checking
    line = re.sub(r"(\.{3,}|…|\s)+$", "", line)
    line = re.sub(r"^(\.{3,}|…|\s)+", "", line)
    
    return line + " "

def ends_with_continuation_string(text: str) -> bool:
    """Determines if a trimmed line ends with an ellipses"""
    
    text = text.rstrip()
    for item in continuation_strings:
        if text.endswith(item):
            return True
    return False











def add_period_if_missing(line: str) -> str:
        """End a string with a period if other punctuation is missing."""
        
        good_endings = (
            ".", "?", "!", '"', "\'", "-", "\\", ",", ";", ":", "\n"
        )
        good_endings_no_space = ("\n", "\\")
        
        stripped_line = line.rstrip()
        has_good_ending = any(stripped_line.endswith(p) for p in good_endings)

        # Adds a period to the end of the sentence if one is needed
        if not has_good_ending :
            stripped_line = stripped_line + ". "
        elif not any(stripped_line.endswith(p) for p in good_endings_no_space):
            # The line ends with a punctuation mark. This makes sure that spaces aren't added after a \n, leading to awkward indents
            stripped_line += " "
        
        return stripped_line

async def setup(bot):
    await bot.add_cog(dmlistener(bot.file_manager, bot.user_manager, bot))

if __name__ == '__main__':
    import main
