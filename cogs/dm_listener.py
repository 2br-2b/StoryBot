import inspect

import discord
import math
import time
from discord.ext import tasks, commands
import re
import json

from config_manager import ConfigManager
import file_manager
import user_manager

# Listens for DMs to add to the story
class dm_listener(commands.Cog):
    def __init__(self, file_manager: file_manager.file_manager, user_manager: user_manager.user_manager, bot: discord.Client):
        self.file_manager = file_manager
        self.user_manager = user_manager
        
        self.bot = bot
        
        self.CHARACTERS_TO_SHOW = 4096
        
        self.config_manager = bot.config_manager


    async def check_for_prefix_command(self, ctx: commands.Context):
        if(await self.config_manager.is_debug_mode() or ctx.author == self.bot.user):
            return
        if(ctx.prefix != "/"):
            msg = f"Prefix commands (like what you just ran, `{ctx.message.content}`) no longer work. You'll have to run that as a slash command.\n\nTry running `/{ctx.message.content[len(self.config_manager.get_prefix()):]}`.\n\nSee https://github.com/2br-2b/StoryBot/issues/31 to learn more, and thank you for your patience during this transition!"
            await self.reply_to_message(context=ctx, content=msg, ephemeral=True)
            raise Exception("Prefixed command")


    async def dm_current_user(self, guild_id: int, message, file = None, embed = None):
        """Sends the given message to the current user"""
        try:
            await (await (await self.bot.fetch_user(int(await self.user_manager.get_current_user(guild_id)))).create_dm()).send(message, embed=embed, file = file)
        
        except discord.ext.commands.errors.HybridCommandError: # Means the user couldn't be DMed
            
            if await self.user_manager.get_current_user(guild_id) == await self.user_manager.get_current_user(guild_id):
                skip_after = True
            else:
                skip_after = False
            
            await self.user_manager.remove_user(guild_id, int(await self.user_manager.get_current_user(guild_id)))
        
            if(skip_after):
                try:
                    await self.new_user(guild_id)
                except ValueError: #This means that there's no users in the list of users. new_user will return an error but will also set the current user to None.
                    pass
            

    async def notify_people(self, guild_id: int):
        """Notifies the current user that it's their turn to add to the story"""
        
        file = await self.file_manager.get_story_file(guild_id)
        await self.dm_current_user(guild_id,
                                   "Your turn.  Respond with a DM to continue the story!  Use a \\ to create a line break.\n\nIf you want the next user to continue your sentence, end your story segment with `...`.\n\n**MAKE SURE THE BOT IS ONLINE BEFORE RESPONDING!**  You will get a confirmation response if your story is received.\n\nHere is the story so far:",
                                   file = file, embed = await self.create_embed(content=self.lastChars(await self.file_manager.getStory(guild_id)), author_name=None, author_icon_url=None))
        
        current_user = await self.bot.fetch_user(int(await self.user_manager.get_current_user(guild_id)))
        
        emb = await self.create_embed(
            author_icon_url=current_user.display_avatar.url,
            author_name=f"It's now {current_user.name}'s turn!"
            )
        
        # Send a message in the story chanel
        channel_int = await self.config_manager.get_story_announcement_channel(guild_id)
        if channel_int != None:
            channel = self.bot.get_channel(channel_int)
            if channel != None:
                try:
                    await channel.send(embed = emb)
                except discord.errors.Forbidden:
                    # TODO: Check for this perm properly
                    pass
    
    @commands.guild_only()
    @commands.before_invoke(check_for_prefix_command)
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
                await self.reply_to_message(content='That story number couldn\'t be found!', context=ctx, ephemeral=True)
                return
        else:
            file = await self.file_manager.get_story_file(proper_guild_id)
            title="The Current Story"
            
        await self.reply_to_message(
            content=self.lastChars(await self.file_manager.getStory(guild_id = proper_guild_id, story_number = archived_story_number)),
            title=title, file = file, context=ctx, ephemeral=True)

    @commands.guild_only()
    @commands.before_invoke(check_for_prefix_command)
    @commands.hybrid_command(name="turn")
    async def turn(self, ctx: commands.Context):
        """Sends a message with the current user's name"""
        
        await self.check_for_prefix_command(ctx)
        
        current_user_id = await self.user_manager.get_current_user(self.get_proper_guild_id(ctx))
        if current_user_id != None:
            current_user = await self.bot.fetch_user(int(current_user_id))
            await self.reply_to_message(author=current_user, context=ctx, ephemeral=True)
        else:
            await self.reply_to_message(content="There is no current user. Join the bot to become the first!", context=ctx, ephemeral=True)

    @commands.hybrid_command(name="help")
    async def help(self, ctx):
        """The help command"""
        
        await self.check_for_prefix_command(ctx)
        
        await self.reply_to_message(context=ctx, 
            content="""This bot is a story bot.  One user will write a part of the story (anywhere from a sentence or two to a couple of paragraphs - your choice!), then another, and so on until the story is complete!
            
    `/join` adds you to the authors, while `/leave` removes you
    `/story` displays the story so far - put a number afterwards to see a past story
    `/turn` displays whose turn it is
    
    Note - these commands only work in servers""", ephemeral=True)

    @commands.guild_only()
    @commands.before_invoke(check_for_prefix_command)
    @commands.hybrid_command(name="skip")
    async def skip(self, ctx: commands.Context):
        """Skip your turn"""
        
        await self.check_for_prefix_command(ctx)
        
        proper_guild_id = self.get_proper_guild_id(ctx)
        current_user_id = await self.user_manager.get_current_user(proper_guild_id)
        
        if str(ctx.author.id) != current_user_id and not await self.config_manager.is_admin(ctx.author.id, proper_guild_id):
            await self.reply_to_message(context=ctx, content="It's not your turn here!")
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
        
        

    @commands.guild_only()
    @commands.before_invoke(check_for_prefix_command)
    @commands.hybrid_command(name="notify")
    async def notify(self, ctx):
        """The command to notify users that it's their turn"""
        
        await self.check_for_prefix_command(ctx)
        
        if not await self.config_manager.is_admin(ctx.author.id, ctx.guild.id):
            await self.reply_to_message(context=ctx, content="Only admins can use this command.", ephemeral=True)
            return
        
        await self.notify_people(self.get_proper_guild_id(ctx))
        
    @commands.guild_only()
    @commands.before_invoke(check_for_prefix_command)
    @commands.hybrid_command(name="time_left")
    async def time_left_command(self, ctx: commands.Context):
        """Says how much time the current user has remaining"""
        
        proper_guild_id = self.get_proper_guild_id(ctx)
        user_id = await self.user_manager.get_current_user(proper_guild_id)
        if user_id == None:
            await self.reply_to_message(content="There is no current user. Join the bot to become the first!", context=ctx, ephemeral=True)
            return
        
        seconds_per_turn = await self.config_manager.get_timeout_days(ctx.guild.id) * 24 * 60 * 60
        timeout_timestamp = int(await self.file_manager.load_timestamp(proper_guild_id))
        current_time = int(time.time())
        seconds_since_timestamp = current_time - timeout_timestamp
        seconds_remaining = seconds_per_turn - seconds_since_timestamp
        
        current_user = await self.bot.fetch_user(int(user_id))
        
        await self.reply_to_message(context=ctx, content="Time remaining: " + dm_listener.print_time(seconds=seconds_remaining + 60) +"\nTime used: " + dm_listener.print_time(seconds=seconds_since_timestamp)+"", ephemeral=True, author=current_user)
        
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
            
            if message.content.startswith("/") or message.content.startswith(self.config_manager.get_prefix()):
                return
            
            user_current_turns = await self.file_manager.get_current_turns_of_user(message.author.id)
            
            if len(user_current_turns) < 1:
                return
            elif len(user_current_turns) == 1:
                proper_guild_id = user_current_turns[0]
            else:
                proper_guild_id = await self.request_guild_for_story_entry(message, user_current_turns)
                
            #self.get_proper_guild_id(message.channel)
            
            if (await self.user_manager.get_current_user(proper_guild_id)) != str(message.author.id):
                await self.reply_to_message(message=message, content="Nice try :stuck_out_tongue_winking_eye:", ephemeral=True)
                return
                
                
            content_to_send = await self.format_story_addition(message.content)
            
            # Add the given line to the story file
            await self.file_manager.addLine(
                guild_id=proper_guild_id,
                line=content_to_send
                )
            
            await self.file_manager.log_action(user_id=message.author.id, guild_id=proper_guild_id, action="write")
            
            # Mirror the messages to a Discord channel
            channel_int = await self.config_manager.get_story_output_channel(proper_guild_id)
            if channel_int != None:
                channel = self.bot.get_channel(channel_int)
                if channel != None:
                    try:
                        await channel.send(content_to_send)
                    except discord.errors.Forbidden:
                        # TODO: Check for this perm properly
                        pass
            
            await self.reply_to_message(message, "Got it!  Thanks!")
            
            await self.user_manager.boost_user(proper_guild_id, int(await self.user_manager.get_current_user(proper_guild_id)))
            
            await self.new_user(proper_guild_id)

    def pieMethod(self, story):
        """The all-powerful pieMethod
        Splits the story into a list of strings if it is too long"""
        MAX_MESSAGE_LENGTH = 1950
        if len(story) >= MAX_MESSAGE_LENGTH:
            split = list()
            for i in range(math.ceil(len(story) / MAX_MESSAGE_LENGTH)):
                if i == math.ceil(len(story) / MAX_MESSAGE_LENGTH):
                    split.append(story[i:len(story) -1])
                else:
                    split.append(story[i:i+MAX_MESSAGE_LENGTH])
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
            
            if len(await self.user_manager.get_unweighted_list(guild_id)) >= 2 and time.time() - await self.file_manager.load_timestamp(guild_id) >= 60 * 60 * 24 * await self.config_manager.get_timeout_days(guild_id): # if the time is over the allotted time
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

    @commands.guild_only()
    @commands.before_invoke(check_for_prefix_command)
    @commands.hybrid_command(name="join")
    async def add(self, ctx: commands.Context):
        """Adds you to the list of authors"""
        
        await self.check_for_prefix_command(ctx)
        guild_id = ctx.guild.id
        
        if(await self.user_manager.get_current_user(guild_id) == None):
            await self.file_manager.set_current_user_id(guild_id, ctx.author.id)
            await self.notify_people(guild_id)
            await self.file_manager.reset_timestamp(guild_id)
        
        await self.user_manager.add_user(guild_id, ctx.author.id)
        await self.reply_to_message(context=ctx, content="Done!")

    @commands.guild_only()
    @commands.before_invoke(check_for_prefix_command)
    @commands.hybrid_command(name="leave")
    async def remove(self, ctx: commands.Context):
        """Removes you from the list of authors"""
        
        await self.check_for_prefix_command(ctx)
        
        proper_guild = self.get_proper_guild_id(ctx)
        
        if await self.user_manager.get_current_user(proper_guild) == str(ctx.author.id):
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

    async def format_story_addition(self, line:str) -> str:
        if(line.startswith(self.config_manager.get_prefix())):
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
            return trim_ellipses(line)
        else:
            return add_period_if_missing(line)
        
        
    async def reply_to_message(self, message: discord.Message = None, content: str = "", context: commands.Context = None, file: discord.File = None, author: discord.User = None, title: str = None, ephemeral = False, view=None) -> discord.Message:
        """Replies the given message

        Args:
            message (discord.abc.Messageable): the message or ctx to reply to
            content (str): the content to reply to
            file (discord.File): the file to embed (if one is needed)
            author (str): the user to display on the embed
        """
        
        if type(message) is "str":
            raise TypeError("`message` should be of type message, not a string! Maybe you meant to set `content`?")
        
        embed = await self.create_embed(content=content, title=title)
        
        if author is None and not message is None:
            author = message.author
        if not author is None:
            embed.set_author(name=author.name, icon_url=author.display_avatar.url)
        
        try:
            if not context is None:
                return await context.send(embed = embed, file = file, mention_author = False, ephemeral=ephemeral, view=view)
            elif not message is None:
                return await message.reply(embed = embed, file = file, mention_author = False, view=view)
            else:
                raise ValueError("Both ctx and message passed to reply_to_message are None")
        except discord.errors.Forbidden:
            # TODO: Check for this perm properly
            pass
          
          
    async def new_user(self, guild_id: int):
        """Chooses a new random user and notifies all relevant parties"""
        await self.file_manager.reset_timestamp(guild_id)
        await self.user_manager.set_random_weighted_user(guild_id)
        
        if await self.user_manager.get_current_user(guild_id) != None:
            await self.notify_people(guild_id)

    def get_proper_guild_id(self, channel: discord.abc.Messageable) -> int:
        if channel.guild is None:
            # TODO: figure out how to implement get_proper_guild_id
            return None
        
        return channel.guild.id

        
    async def request_guild_for_story_entry(self, message: discord.Message, user_current_turns: list[int]) -> int:
        server_json = []
        for guild_id in user_current_turns:
            guild_name = self.bot.get_guild(guild_id).name
            server_json.append({"guild id": guild_id, "guild name": guild_name})
        
        server_json.sort(key=lambda k: k["guild name"])
        
        view = DropdownView(server_json)
        
        my_message = await self.reply_to_message(message = message, content="Which server should this be added to?", view=view, ephemeral= True)
        
        await view.wait()
        
        await my_message.delete()
        
        return int(view.value)
    
    async def create_embed(self, content=None, color=None, title=None, author_name=None, author_icon_url=None) -> discord.Embed:
        """Creates an embed with the given parameters. All values have defaults if not given."""
        if color == None:
            color = await self.config_manager.get_embed_color()
        emb = discord.Embed(description=content, color=color, title=title)
        if author_name != None or author_icon_url != None:
            emb.set_author(name=author_name, icon_url=author_icon_url)
        
        return emb
    
    @commands.before_invoke(check_for_prefix_command)
    @commands.hybrid_command(name="my_turns")
    async def my_turns(self, ctx: commands.Context):
        """Lists all of the servers where it's currently your turn"""
        user_current_turns = await self.file_manager.get_current_turns_of_user(ctx.author.id)
        
        if len(user_current_turns) < 1:
            text = "It's not your turn in any servers!"
        else:
            text = ""
            for guild_id in user_current_turns:
                guild_name = self.bot.get_guild(guild_id).name
                text += guild_name + "\n"
            text = text[:-1]
            
        await self.reply_to_message(context=ctx, content=text, title=f"{ctx.author.name}'s current turns", ephemeral=True)
            

        
class DropdownView(discord.ui.View):
    def __init__(self, server_json):
        super().__init__()

        # Adds the dropdown to our view object.
        self.add_item(ServerChooser(server_json, self))
        self.guild_id = None
        self.value = None

class ServerChooser(discord.ui.Select):
    def __init__(self, guild_json, view):
        guilds = []

        for item in guild_json:
            option = discord.SelectOption(label=item["guild name"],
                                          value=item["guild id"])
            
            guilds.append(option)
            
        self.vv = view
        super().__init__(placeholder='Which server is this story for?', min_values=1, max_values=1, options=guilds)
        
    async def callback(self, interaction: discord.Interaction):
        self.vv.value = self.values[0]
        self.vv.guild_id = self.values[0]
        self.vv.stop()


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

