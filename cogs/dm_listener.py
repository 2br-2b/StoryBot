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
class dm_listener(commands.Cog):
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
    
    @commands.hybrid_command(name="story")
    async def story(self, ctx: commands.Context, archived_story_number:int = 0):
        """Sends a reply with the requested story
        If there is a number, the given story number will be returned"""
        
        # TODO: use file_manager.py here
        
        if archived_story_number != 0:
            try:
                file = discord.File("story {0}.txt".format(archived_story_number), filename="story {0}.txt".format(archived_story_number))
                title = "Story " + str(archived_story_number)
            except FileNotFoundError:
                await self.reply_to_message(content='That story number couldn\'t be found!', context=ctx, single_user=True)
                return
        else:
            file = discord.File("story.txt", filename="story.txt")
            title="The Current Story"
            
        await self.reply_to_message(content=self.lastChars(self.file_manager.getStory(archived_story_number)), title=title, file = file, context=ctx, single_user=True)

    @commands.hybrid_command(name="turn")
    async def turn(self, ctx: commands.Context):
        """Sends a message with the current user's name"""
        current_user = await self.bot.fetch_user(int(self.user_manager.get_current_user()))
        
        #ctx.message.guild.get_member(int(self.user_manager.get_current_user()))
        
        await self.reply_to_message(author=current_user, context=ctx, single_user=True)

    @commands.hybrid_command(name="help")
    async def help(self, ctx):
        """The help command"""
        
        await self.reply_to_message(context=ctx, 
            content="""This bot is a story bot.  One user will write a part of the story (anywhere from a sentence or two to a couple of paragraphs - your choice!), then another, and so on until the story is complete!
            
    `""" + config.PREFIX + "add` adds you to the authors, while `"+config.PREFIX + """remove` removes you
    `""" + config.PREFIX + """story` displays the story so far - put a number afterwards to see a past story
    `""" + config.PREFIX + "turn` displays whose turn it is\n\nSlash commands now work in servers; however, only prefixed commands work in DMs", single_user=True)

    @commands.hybrid_command(name="skip")
    async def skip(self, ctx):
        """Skips the current user"""
        
        if str(ctx.author.id) != self.user_manager.get_current_user() and not ctx.author.id in config.ADMIN_IDS:
            await self.reply_to_message(context=ctx, content="It's not your turn!")
            return
        await self.reply_to_message(context=ctx, content="Skipping :(")
        self.current_user = self.user_manager.set_random_weighted_user()
        self.reset_timestamp()

        await self.notify_people()
        await self.wait_and_check()

    @commands.hybrid_command(name="notify")
    @commands.is_owner()
    async def notify(self, ctx):
        """The command to notify users that it's their turn"""
        
        if not ctx.author.id in config.ADMIN_IDS:
            await self.reply_to_message(context=ctx, content="Only admins can use this command.", single_user=True)
            return
        
        await self.notify_people()

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
                
                current = await self.bot.fetch_user(int(self.user_manager.get_current_user()))
                
                if config.SEND_STORY_AS_EMBED_IN_CHANNEL:
                    content_to_send = None
                    emb = create_embed(
                        author_name=current.name,
                        author_icon_url=current.display_avatar.url,
                        content=self.format_story_addition(message.content)
                    )
                else:
                    content_to_send = self.format_story_addition(message.content)
                    emb = None
                
                # Mirror the messages to a Discord channel
                for channel in config.STORY_OUTPUT_CHANNELS:
                    await self.bot.get_channel(channel).send(content_to_send, embed = emb)
                
                await self.reply_to_message(message, "Got it!  Thanks!")
                
                self.user_manager.boost_user(self.current_user)
                self.current_user = self.user_manager.set_random_weighted_user(add_last_user_to_queue = True)
                self.reset_timestamp()

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
        self.current_user = self.user_manager.set_random_weighted_user(add_last_user_to_queue = True)
        print('done changing user to '+str(self.current_user)+'. About to notify people...')
        await self.notify_people()

        self.last_checked_user = self.current_user
        
        self.reset_timestamp()

    @tasks.loop(seconds=60 * 60) # Check back every hour
    async def timeout_checker(self):
        """Will skip the current user's turn if they don't respond in the specified amount of time"""
        if time.time() - self.load_timestamp() >= 60 * 60 * 24 * config.TIMEOUT_DAYS: # if the time is over the allotted time
            print('about to timeout for '+str(self.current_user))
            await self.timeout_happened()
            print('timeout happened. New user is '+str(self.current_user))
            self.reset_timestamp()
        
        print('checked: {0} seconds at {1}'.format(time.time() - self.load_timestamp(), time.time()))


    @commands.Cog.listener()
    async def on_ready(self):
        self.timeout_checker.start()

    def cog_unload(self):
        self.timeout_checker.cancel()

    @commands.hybrid_command(name="add")
    async def add(self, ctx):
        """Adds a user to the list of participants"""
        
        self.user_manager.add_user(ctx.author.id)
        await self.reply_to_message(context=ctx, content="Done!")

    @commands.hybrid_command(name="remove")
    async def remove(self, ctx):
        """Removes a user from the list of participants"""
        
        self.user_manager.remove_user(ctx.author.id)
        await self.reply_to_message(context=ctx, content="Done!")

    @staticmethod
    def load_timestamp(filename: str = "timestamp.txt") -> float:
        """Returns the timestamp if it exists. If it doesn't, it'll reset the timestamp and return the new one."""

        try:
            with open(filename, "r") as f:
                return float(f.read())
        except FileNotFoundError:
            print("Timestamp not found. Resetting timestamp...")
            dm_listener.reset_timestamp()
            return dm_listener.load_timestamp()
        except ValueError:
            dm_listener.reset_timestamp()
            raise RuntimeWarning("Timestamp has been corrupted. I have reset the timestamp, but if this keeps happening, something's wrong.")

    @staticmethod
    def reset_timestamp(filename:str = "timestamp.txt") -> float:
        """Resets the timestamp to the current time"""
        now = time.time()
        with open(filename, "w") as f:
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
        
        
    async def reply_to_message(self, message: discord.Message = None, content: str = "", context: commands.Context = None, file: discord.File = None, author: discord.User = None, title: str = None, single_user = False):
        """Replies the given message

        Args:
            message (discord.abc.Messageable): the message or ctx to reply to
            content (str): the content to reply to
            file (discord.File): the file to embed (if one is needed)
            author (str): the user to display on the embed
        """
        
        if type(message) is "str":
            raise TypeError("`message` should be of type message, not a string! Maybe you meant to set `content`?")
        
        embed = create_embed(content=content, title=title)
        
        if author is None and not message is None:
            author = message.author
        if not author is None:
            embed.set_author(name=author.name, icon_url=author.display_avatar.url)
            
        if not context is None:
            await context.send(embed = embed, file = file, mention_author = False, ephemeral=single_user)
        elif not message is None:
            await message.reply(embed = embed, file = file, mention_author = False)
        else:
            raise ValueError("Both ctx and message passed to reply_to_message are None")
            
        


def create_embed(content=None, color=config.EMBED_COLOR, title=None, author_name=None, author_icon_url=None) -> discord.Embed:
    """Creates an embed with the given parameters. All values have defaults if not given."""
    emb = discord.Embed(description=content, color=color, title=title)
    if author_name != None:
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
    await bot.add_cog(dm_listener(bot.file_manager, bot.user_manager, bot))

if __name__ == '__main__':
    import main
