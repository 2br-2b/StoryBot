import inspect

import discord
import math
import time
from discord.ext import tasks, commands
import re

import config_manager
import file_manager
import user_manager

# Listens for DMs to add to the story
class dm_listener(commands.Cog):
    def __init__(self, file_manager: file_manager.file_manager, user_manager: user_manager.user_manager, bot):
        self.file_manager = file_manager
        self.user_manager = user_manager
        
        self.bot = bot

        # The timestamp keeps track of when the last user was notified, so that even if the bot goes down, it still knows how much longer the current user has to continue the story
        self._notif_line_cont = False
        
        self.CHARACTERS_TO_SHOW = 4096


    async def check_for_prefix_command(self, ctx: commands.Context, just_removed = False):
        if(config_manager.is_debug_mode()):
            return
        if(ctx.prefix != "/"):
            if(just_removed):
                msg = f"Just a heads up: prefix commands (like what you just ran, `{ctx.message.content}`) work for now, but if you choose to use this bot again in the future, you'll need to switch over to slash commands.\n\nTo rejoin, you'll have to run `/add` as opposed to `{config_manager.get_prefix()}add`.\n\nSee https://github.com/2br-2b/StoryBot/issues/31 to learn more, and thank you for your patience during this transition!"
            else:
                msg = f"Just a heads up: prefix commands (like what you just ran, `{ctx.message.content}`) work for now, but you'll want to switch over to slash commands soon.\n\nIn the future, you'll need to run that command by typing `/{ctx.message.content[len(config_manager.get_prefix()):]}`.\n\nSee https://github.com/2br-2b/StoryBot/issues/31 to learn more, and thank you for your patience during this transition!"
            
            await (await ctx.author.create_dm()).send(msg)


    async def dm_current_user(self, guild_id: int, message, file = None, embed = None):
        """Sends the given message to the current user"""
        
        await (await (await self.bot.fetch_user(int(await self.user_manager.get_current_user(guild_id)))).create_dm()).send(message, embed=embed, file = file)
        if self._notif_line_cont:
            self._notif_line_cont = False
            await self.dm_current_user(guild_id, "**Please pick up the writing in the middle of the last sentence.**")
            

    async def notify_people(self, guild_id: int):
        """Notifies the current user that it's their turn to add to the story"""
        
        file = await self.file_manager.get_story_file(guild_id)
        await self.dm_current_user(guild_id, """Your turn.  Respond with a DM to continue the story!  Use a \ to create a line break.
            
            **MAKE SURE THE BOT IS ONLINE BEFORE RESPONDING!**  You will get a confirmation response if your story is received.
            
            Here is the story so far:""", file = file, embed = create_embed(content=self.lastChars(await self.file_manager.getStory(guild_id)), author_name=None, author_icon_url=None))
        
        current_user = await self.bot.fetch_user(int(await self.user_manager.get_current_user(guild_id)))
        
        emb = create_embed(
            author_icon_url=current_user.display_avatar.url,
            author_name=f"It's now {current_user.name}'s turn!"
            )
        
        # Send a message in the story chanel
        for channel in config_manager.get_story_announcement_channels(guild_id):
            await self.bot.get_channel(channel).send(embed = emb)
    
    @commands.hybrid_command(name="story")
    async def story(self, ctx: commands.Context, archived_story_number:int = 0):
        """Sends a reply with the requested story
        If there is a number, the given story number will be returned"""
        
        await self.check_for_prefix_command(ctx)
        
        proper_guild_id = self.get_proper_guild_id(ctx)
        
        if archived_story_number != 0:
            try:
                file = await self.file_manager.get_story_file(proper_guild_id, archived_story_number)
                title = "Story " + str(archived_story_number)
            except FileNotFoundError:
                await self.reply_to_message(content='That story number couldn\'t be found!', context=ctx, single_user=True)
                return
        else:
            file = await self.file_manager.get_story_file(proper_guild_id)
            title="The Current Story"
            
        await self.reply_to_message(
            content=self.lastChars(await self.file_manager.getStory(guild_id = proper_guild_id, story_number = archived_story_number)),
            title=title, file = file, context=ctx, single_user=True)

    @commands.hybrid_command(name="turn")
    async def turn(self, ctx: commands.Context):
        """Sends a message with the current user's name"""
        
        await self.check_for_prefix_command(ctx)
        
        current_user_id = await self.user_manager.get_current_user(self.get_proper_guild_id(ctx))
        if current_user_id != None:
            current_user = await self.bot.fetch_user(int(current_user_id))
            await self.reply_to_message(author=current_user, context=ctx, single_user=True)
        else:
            await self.reply_to_message(content="There is no current user. Join the bot to become the first!", context=ctx, single_user=True)

    @commands.hybrid_command(name="help")
    async def help(self, ctx):
        """The help command"""
        
        await self.check_for_prefix_command(ctx)
        
        await self.reply_to_message(context=ctx, 
            content="""This bot is a story bot.  One user will write a part of the story (anywhere from a sentence or two to a couple of paragraphs - your choice!), then another, and so on until the story is complete!
            
    `/add` adds you to the authors, while `/remove` removes you
    `/story` displays the story so far - put a number afterwards to see a past story
    `/turn` displays whose turn it is""", single_user=True)

    @commands.hybrid_command(name="skip")
    async def skip(self, ctx: commands.Context):
        """Skips the current user"""
        
        await self.check_for_prefix_command(ctx)
        
        proper_guild_id = self.get_proper_guild_id(ctx)
        current_user_id = await self.user_manager.get_current_user(proper_guild_id)
        
        if str(ctx.author.id) != current_user_id and not config_manager.is_admin(ctx.author.id, proper_guild_id):
            await self.reply_to_message(context=ctx, content="It's not your turn!")
            return
        
        try:
            if(current_user_id != None):
                await self.file_manager.log_action(user_id=int(current_user_id), guild_id=proper_guild_id, action="skip")
            else:
                await self.file_manager.log_action(user_id=0, guild_id=proper_guild_id, action="skip")
            
            await self.new_user(proper_guild_id)
            await self.reply_to_message(context=ctx, content="Skipping :(")
        except ValueError:
            await self.reply_to_message(context=ctx, content="There are no users in the queue to skip to!")
        
        

    @commands.hybrid_command(name="notify")
    async def notify(self, ctx):
        """The command to notify users that it's their turn"""
        
        await self.check_for_prefix_command(ctx)
        
        if not config_manager.is_admin(ctx.author.id, ctx.guild.id):
            await self.reply_to_message(context=ctx, content="Only admins can use this command.", single_user=True)
            return
        
        await self.notify_people(self.get_proper_guild_id(ctx))
        
    @commands.hybrid_command(name="time_left")
    async def time_left_command(self, ctx: commands.Context):
        """Says how much time the current user has remaining"""
        
        await self.check_for_prefix_command(ctx)
        
        proper_guild_id = self.get_proper_guild_id(ctx)
        
        seconds_per_turn = config_manager.get_timeout_days(ctx.guild.id) * 24 * 60 * 60
        timeout_timestamp = int(await self.file_manager.load_timestamp(proper_guild_id))
        current_time = int(time.time())
        seconds_since_timestamp = current_time - timeout_timestamp
        seconds_remaining = seconds_per_turn - seconds_since_timestamp
        
        current_user = await self.bot.fetch_user(int(await self.user_manager.get_current_user(proper_guild_id)))
        
        await self.reply_to_message(context=ctx, content="Time remaining: " + dm_listener.print_time(seconds=seconds_remaining + 60) +"\nTime used: " + dm_listener.print_time(seconds=seconds_since_timestamp)+"", single_user=True, author=current_user)
        
    @staticmethod
    def print_time(seconds:int, include_seconds: bool = False) -> str:
        """Generates a printable string based on a given number of seconds. `timedelta` has a built-in method for this, but it kept saying `Python int too large to convert to C int`

        Args:
            seconds (int): the amount of seconds to print

        Returns:
            str: the printable string. If the amount of seconds is negative, this will return "Should time out soon..."
        """
        
        if include_seconds:
            print_seconds = seconds % 60
        print_minutes = int((seconds/60) % 60)
        print_hours = int((seconds/3600) % 24)
        print_days = int(seconds/(60 * 60 * 24))
        
        if(print_days < 0):
            return "Should time out soon..."
        elif(print_days > 0):
            s = f"{print_days} d, "
        else:
            s = ""
        
        s += f"{print_hours} h, {print_minutes} m"
        
        if include_seconds:
            s += f", {print_seconds} s"
        
        return s
        

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Checks if the message should be added the story, and if it is, appends it"""

        if message.guild is None and message.author != self.bot.user:
            proper_guild_id = self.get_proper_guild_id(message.channel)
            
            if await self.user_manager.get_current_user(proper_guild_id) == str(message.author.id):
                if message.content.startswith("/") or message.content.startswith(config_manager.get_prefix()):
                    return
                
                content_to_send = self.format_story_addition(message.content)
                
                # Add the given line to the story file
                await self.file_manager.addLine(
                    guild_id=proper_guild_id,
                    line=content_to_send
                    )
                
                await self.file_manager.log_action(user_id=message.author.id, guild_id=proper_guild_id, action="add")
                
                # Mirror the messages to a Discord channel
                for channel in config_manager.get_story_output_channels(proper_guild_id):
                    await self.bot.get_channel(channel).send(content_to_send)
                
                await self.reply_to_message(message, "Got it!  Thanks!")
                
                await self.user_manager.boost_user(proper_guild_id, int(await self.user_manager.get_current_user(proper_guild_id)))
                
                await self.new_user(proper_guild_id)

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

    async def timeout_happened(self, guild_id: int):
        """Skips the current user's turn if they don't respond in the specified amount of time"""
        
        print('Timing out...') 
        await self.dm_current_user(guild_id, 'You took too long!  You\'ll have a chance to add to the story later - don\'t worry!')
        current_user_id = int(await self.user_manager.get_current_user(guild_id))
        await self.user_manager.unboost_user(guild_id, current_user_id)
        await self.file_manager.log_action(user_id=current_user_id, guild_id=guild_id, action="timeout")
        await self.new_user(guild_id)

    @tasks.loop(seconds=60 * 60) # Check back every hour
    async def timeout_checker(self):
        """Will skip the current user's turn if they don't respond in the specified amount of time"""
        
        for guild_id in await self.file_manager.get_all_guild_ids():
            
            if time.time() - await self.file_manager.load_timestamp(guild_id) >= 60 * 60 * 24 * config_manager.get_timeout_days(guild_id): # if the time is over the allotted time
                await self.timeout_happened(guild_id)
                


    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.timeout_checker.start()
        except RuntimeError as e:
            if not str(e) == "Task is already launched and is not completed.":
                raise RuntimeError(str(e))


    def cog_unload(self):
        self.timeout_checker.cancel()

    @commands.hybrid_command(name="add")
    async def add(self, ctx):
        """Adds a user to the list of participants"""
        
        await self.check_for_prefix_command(ctx)
        
        await self.user_manager.add_user(self.get_proper_guild_id(ctx), ctx.author.id)
        await self.reply_to_message(context=ctx, content="Done!")

    @commands.hybrid_command(name="remove")
    async def remove(self, ctx: commands.Context):
        """Removes a user from the list of participants. If it is their turn, it also skips them"""
        
        await self.check_for_prefix_command(ctx, just_removed=True)
        
        proper_guild = self.get_proper_guild_id(ctx)
        
        if self.user_manager.get_current_user(proper_guild) == str(ctx.author.id):
            skip_after = True
        else:
            skip_after = False
        
        await self.user_manager.remove_user(proper_guild, ctx.author.id)
        
        if(skip_after):
            try:
                await self.new_user(proper_guild)
            except ValueError: #This means that there's no users in the list of users. new_user will return an error but will also set the current user to None.
                pass
        
        await self.reply_to_message(context=ctx, content="Done!")

    def format_story_addition(self, line:str) -> str:
        if(line.startswith(config_manager.get_prefix())):
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
          
          
    async def new_user(self, guild_id: int):
        """Chooses a new random user and notifies all relevant parties"""
        await self.user_manager.set_random_weighted_user(guild_id, add_last_user_to_queue = True)
        
        print("New current user: " + await self.user_manager.get_current_user(guild_id))
        await self.file_manager.reset_timestamp(guild_id)
        await self.notify_people(guild_id)

    def get_proper_guild_id(self, channel: discord.abc.Messageable) -> int:
        if channel.guild is None:
            # TODO: figure out how to implement this
            return config_manager.get_default_guild_id()
        
        return channel.guild.id
        
        

        

def create_embed(content=None, color=config_manager.get_embed_color(), title=None, author_name=None, author_icon_url=None) -> discord.Embed:
    """Creates an embed with the given parameters. All values have defaults if not given."""
    emb = discord.Embed(description=content, color=color, title=title)
    if author_name != None or author_icon_url != None:
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
