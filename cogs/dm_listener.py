import discord
import math
import time
from discord.ext import tasks, commands
from discord import app_commands
import re
from enum import Enum

from config_manager import ConfigManager
import file_manager
import user_manager
from discord.ext.commands import MissingPermissions
import storybot_exceptions


class AvailableSettingsToModify(Enum):
    AnnouncementChannel=1
    StoryOutputChannel=2
    TimeoutDays=3
    ResetCurrentPlayerTimeRemaining=4
    SafeModeEnabled=5

# Listens for DMs to add to the story
class dm_listener(commands.Cog):
    def __init__(self, file_manager: file_manager.file_manager, user_manager: user_manager.user_manager, bot: discord.Client):
        self.file_manager = file_manager
        self.user_manager = user_manager
        
        self.bot = bot
        
        self.CHARACTERS_TO_SHOW = 4096
        
        self.config_manager = bot.config_manager

    async def dm_current_user(self, guild_id: int, message, file = None, embed = None):
        """Sends the given message to the current user"""
        try:
            await self.dm_user(user_id=int(await self.user_manager.get_current_user(guild_id)), message=message, file=file, embed=embed)
        
        except discord.ext.commands.errors.HybridCommandError: # Means the user couldn't be DMed
            await self.remove_user_plus_skip_logic(guild_id, int(await self.user_manager.get_current_user(guild_id)))
            
    async def dm_user(self, user_id: int, message, file = None, embed = None):
        """Sends the given message to the current user"""
        await (await (await self.bot.fetch_user(user_id)).create_dm()).send(message, embed=embed, file = file)

    async def notify_people(self, guild_id: int):
        """Notifies the current user that it's their turn to add to the story"""
        
        file = await self.file_manager.get_story_file(guild_id)

        try:
            await self.dm_current_user(guild_id,
                                   "Your turn.  Respond with a DM to continue the story!  Use a \\ to create a line break.\n\nIf you want the next user to continue your sentence, end your story segment with `...`.\n\n**MAKE SURE THE BOT IS ONLINE BEFORE RESPONDING!**  You will get a confirmation response if your story is received.\n\nHere is the story so far:",
                                   file = file, embed = await self.create_embed(content=self.lastChars(await self.file_manager.getStory(guild_id)), author_name=None, author_icon_url=None))
        except discord.errors.Forbidden:
            # Can't DM the user
            user_id = await self.user_manager.get_current_user(guild_id=guild_id)
            print(f"Kicking {user_id} from {guild_id} because I can't DM them while running notify_people")
            await self.user_manager.remove_user(guild_id, user_id=user_id)
            await self.new_user(guild_id=guild_id)
        
        current_user = await (await self.bot.fetch_guild(guild_id)).fetch_member(int(await self.user_manager.get_current_user(guild_id)))
        
        emb = await self.create_embed(
            author_icon_url=current_user.display_avatar.url,
            author_name=f"It's now {current_user.display_name}'s turn!"
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
    @commands.hybrid_command(name="story")
    async def story(self, ctx: commands.Context, archived_story_number:int = 0, public: bool = True):
        """Sends a reply with the requested story
        If there is a number, the given story number will be returned"""
        
        proper_guild_id = self.get_proper_guild_id(ctx)
        
        if archived_story_number != 0:
            try:
                file = await self.file_manager.get_story_file(proper_guild_id, archived_story_number)
                title = "Story " + str(archived_story_number)
            except FileNotFoundError:
                await self.reply_to_message(content='That story number couldn\'t be found!', context=ctx, ephemeral=not public, error=True)
                return
        else:
            file = await self.file_manager.get_story_file(proper_guild_id)
            title="The Current Story"
            
        await self.reply_to_message(
            content=self.lastChars(await self.file_manager.getStory(guild_id = proper_guild_id, story_number = archived_story_number)),
            title=title, file = file, context=ctx, ephemeral=not public)

    @commands.guild_only()
    @commands.hybrid_command(name="turn")
    async def turn(self, ctx: commands.Context, public: bool = False):
        """Sends a message with the current user's name"""
        
        current_user_id = await self.user_manager.get_current_user(self.get_proper_guild_id(ctx))
        if current_user_id != None:
            current_user = await ctx.guild.fetch_member(int(current_user_id))
            await self.reply_to_message(author_name=current_user.display_name, author_icon_url=current_user.display_avatar.url, context=ctx, ephemeral=not public)
        else:
            await self.reply_to_message(content="There is no current user. Join the bot to become the first!", context=ctx, ephemeral=not public, error=True)

    @app_commands.command(name="help")
    async def help(self, interaction: discord.Interaction, show_admin_commands:bool = False, public: bool = False):
        """The help command. Nothing suspicious at all going on here!"""
        
        content="""This bot is a story bot.  One user will write a part of the story (anywhere from a sentence or two to a couple of paragraphs - your choice!), then another, and so on until the story is complete!

        - `/join` adds you to the authors, while `/leave` removes you
        - `/story` displays the story so far - put a number afterwards to see a past story
        - `/skip` skips your turn (in case you don't have time to write)
        - `/turn` displays whose turn it is in this server. If it's your turn, DM the bot to write something!
        - `/my_turns` shows all the servers where it's your turn. If it's your turn in multiple, when you send the bot a story, it'll ask you which you're writing for"""
    
        if show_admin_commands:
            if not public:
                user_id = interaction.user.id
                
                if interaction.guild == None:
                    content = """A direct message? Clever. I see you wish to learn the ways of the admins. Very well, I shall teach you. But beware: these commands only work in servers.
                    
                    - `/configure` brings balance to the story by letting admins prepare the bot
                    - `/ban` and `/unban` are the yin and yang of the bot, representing life and death. `/kick` acts as their center, not quite causing destruction, yet still bringing death to the server
                    - `/undo` permits people to change their ways, perhaps undoing damages done by those seeking to destroy the balance
                    - `/set_turn` is the paradox, for it disrupts the balance, yet allows for greater balance together
                    - `/archive_story` is the great reset, allowing people to begin again
                    
                    If you wish for regular help, set `public` to True"""
                    
                else:
                    if await self.is_moderator(user_id, interaction.channel):
                        content = """But of course! I will show you all the ways of the StoryBot Moderators.
                        
                        - `/configure` shows all the ways you can troll your subjects
                        - `/kick` and `/ban` will fortify your defenses against the trolls of the internet
                        - `/unban` can be used to pardon the plebs who have offended your grace
                        - `/undo` will fix the errors of your subjects by nullifying their contributions
                        - `/set_turn` allows you to grant favors to your closest subjects
                        - `/archive_story` will bring closure to your story and allow you to begin again
                        
                        If you wish for normal "advice", set `public` on this command to True"""
                    else:
                        content = """Heh? An imposter? Well, I suppose I can show you all of the ways by which you will be punished.
                        
                        - `/configure` will give your lords the power to manipulate the masses
                        - `/kick`, `/ban`, and `/unban` represent the powers your lord has over all members of the server
                        - `/undo` shows how futile your writings are, as they can be wiped away in an instant
                        - `/set_turn` can be used to alter the flow of time (and the story)
                        - `/archive_story` shall be used to complete quests and begin new ones
                        
                        If you wish do not wish to be humiliated again, run this command with `public` set to True"""
            
            else:
                content = """Here is a list of the admin-only commands:
                        
                    - `/configure` changes the bot's settings
                    - `/kick`, `/ban`, and `/unban` have obvious functions
                    - `/undo` deletes the most recent addition to the story (but doesn't remove the message from the story output channel)
                    - `/set_turn` changes the current user to a user of your choice. This can be used along with `/undo` to reverse the effects of a turn!
                    - `/archive_story` archives the current story and lets you start over. Don't worry - you'll still be able to read the old story!"""
                        
                        
        await self.reply_to_message(interaction=interaction, content=content, ephemeral=not public)

    @commands.guild_only()
    @commands.hybrid_command(name="skip")
    async def skip(self, ctx: commands.Context, public: bool = False):
        """Skip your turn"""
        
        proper_guild_id = self.get_proper_guild_id(ctx)
        current_user_id = await self.user_manager.get_current_user(proper_guild_id)
        
        if str(ctx.author.id) != current_user_id and not await self.is_moderator(ctx.author.id, ctx.channel):
            await self.reply_to_message(context=ctx, content="It's not your turn here!", error=True, ephemeral=not public)
            return
        
        try:
            if(current_user_id != None):
                await self.file_manager.log_action(user_id=int(current_user_id), guild_id=proper_guild_id, XSS_WARNING_action="skip")
            else:
                await self.file_manager.log_action(user_id=0, guild_id=proper_guild_id, XSS_WARNING_action="skip")
            
            await self.new_user(proper_guild_id)
            await self.reply_to_message(context=ctx, content="Skipping :(", ephemeral=not public)
        except ValueError:
            await self.reply_to_message(context=ctx, content="There are no users in the queue to skip to!", error=True, ephemeral=not public)
        
    @commands.guild_only()
    @commands.hybrid_command(name="time_left")
    async def time_left_command(self, ctx: commands.Context, public: bool = False):
        """Says how much time the current user has remaining"""
        
        proper_guild_id = self.get_proper_guild_id(ctx)
        user_id = await self.user_manager.get_current_user(proper_guild_id)
        if user_id == None:
            await self.reply_to_message(content="There is no current user. Join the bot to become the first!", context=ctx, ephemeral=not public, error=True)
            return
        
        seconds_per_turn = await self.config_manager.get_timeout_days(ctx.guild.id) * 24 * 60 * 60
        timeout_timestamp = int(await self.file_manager.load_timestamp(proper_guild_id))
        current_time = int(time.time())
        seconds_since_timestamp = current_time - timeout_timestamp
        seconds_remaining = seconds_per_turn - seconds_since_timestamp
        
        current_user = await ctx.guild.fetch_member(int(user_id))
        
        await self.reply_to_message(context=ctx, content=f"Time remaining: {dm_listener.print_time(seconds=seconds_remaining + 60)}\nTime used: {dm_listener.print_time(seconds=seconds_since_timestamp)}", ephemeral=not public, author_name=current_user.display_name, author_icon_url=current_user.display_avatar.url)
        
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
                # This means the user had turns in multiple servers, entered input and received the prompt to choose a server, then waited until it was no longer their turn (either by answering another prompt or timing out) to respond. If unpatched, users could send messages after their turn ends.
                await self.reply_to_message(message=message, content="Nice try :stuck_out_tongue_winking_eye:", ephemeral=True)
                return
                
            content_to_send = await self.format_story_addition(message.content)
            
            if await self.config_manager.get_is_safe_mode_activated(proper_guild_id):
                content_to_send = await self.file_manager.filter_profanity(content_to_send)
            
            # Add the given line to the story file
            await self.file_manager.addLine(
                guild_id=proper_guild_id,
                line=content_to_send
                )
            
            # Mirror the messages to a Discord channel
            channel_int = await self.config_manager.get_story_output_channel(proper_guild_id)
            sent_message = None
            sent_message_id = None
            if channel_int != None:
                channel = self.bot.get_channel(channel_int)
                if channel != None:
                    try:
                        # Makes sure that if someone sends a longer message because they have Discord Nitro, the bot will still send the entire story
                        for story_chunk in pieMethod(content_to_send):
                            sent_message = await channel.send(story_chunk)
                            sent_message_id = sent_message.id
                            
                    except discord.errors.Forbidden:
                        # TODO: Check for this perm properly
                        pass
                    
            await self.file_manager.log_action(user_id=message.author.id, guild_id=proper_guild_id, XSS_WARNING_action="write", characters_sent=len(content_to_send), sent_message_id=sent_message_id)
            
            await self.reply_to_message(message, "Got it!  Thanks!")
            
            await self.user_manager.boost_user(proper_guild_id, int(await self.user_manager.get_current_user(proper_guild_id)))
            
            await self.new_user(proper_guild_id)

    def lastChars(self, story):
        """Returns the last self.CHARACTERS_TO_SHOW characters of the story"""
        
        if(len(story) > self.CHARACTERS_TO_SHOW):
            return story[len(story) - self.CHARACTERS_TO_SHOW:len(story) -1]
        else:
            return story

    async def timeout_happened(self, guild_id: int):
        """Skips the current user's turn if they don't respond in the specified amount of time"""
        
        print(f'Timing out {guild_id}...') 
        current_user_id = int(await self.user_manager.get_current_user(guild_id))
        try:
            await self.dm_current_user(guild_id, f"You took too long! Your turn was skipped in {self.bot.get_guild(guild_id).name}. You\'ll have a chance to add to the story later - don\'t worry!")
            await self.user_manager.unboost_user(guild_id, current_user_id)
        except discord.errors.Forbidden:
            print(f"Kicked {current_user_id} from {guild_id} due to a 403 error")
            await self.user_manager.remove_user(guild_id=guild_id, user_id=current_user_id)
        
        await self.file_manager.log_action(user_id=current_user_id, guild_id=guild_id, XSS_WARNING_action="timeout")
        await self.new_user(guild_id)

    @tasks.loop(seconds=60 * 60) # Check back every hour
    async def timeout_checker(self):
        """Will skip the current user's turn if they don't respond in the specified amount of time"""
        now = time.time()
        for guild_id in await self.file_manager.get_all_guild_ids():
            
            # Make sure there's more than one user in the server before timing anyone out
            if len(await self.user_manager.get_unweighted_list(guild_id)) >= 2:
                timeout_days = await self.config_manager.get_timeout_days(guild_id)
                current_timestamp = await self.file_manager.load_timestamp(guild_id)
                
                # Check if their time is over the allotted time
                if now - current_timestamp >= 60 * 60 * 24 * timeout_days:
                    await self.timeout_happened(guild_id)
                    
                # Give people a warning that they're about to time out
                elif timeout_days >= 3 and now - current_timestamp >= 60 * 60 * 24 * (timeout_days - 1) and not await self.file_manager.get_notified(guild_id):
                    print(f"oy! {guild_id}")
                    guild_name = self.bot.get_guild(guild_id).name
                    try:
                        await self.dm_current_user(guild_id=guild_id, message=f"Heads up - you're about to time out in **{guild_name}**! You have around a day left before your turn is automatically skipped.\n\nIf you want to pass on this turn, go to {guild_name} and run `/skip`.")
                    except discord.errors.Forbidden:
                        pass
                    await self.file_manager.set_notified(guild_id, True)
                    
    @tasks.loop(seconds=60 * 60 * 2) # Check back every 2 hours
    async def unpause_users(self):
        #Guild_id is first, then user_id
        tuples = await self.user_manager.unpause_all_necessary_users()
        for letuple in tuples:
            await self.dm_user(user_id=letuple[1], message=f"You have been automatically unpaused in {(await self.bot.fetch_guild(letuple[0])).name}`!")
            

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            self.timeout_checker.start()
        except RuntimeError as e:
            if not str(e) == "Task is already launched and is not completed.":
                raise RuntimeError(str(e))
            
        try:
            self._update_status_loop.start()
        except RuntimeError as e:
            if not str(e) == "Task is already launched and is not completed.":
                raise RuntimeError(str(e))
            
        try:
            self.unpause_users.start()
        except RuntimeError as e:
            if not str(e) == "Task is already launched and is not completed.":
                raise RuntimeError(str(e))


    def cog_unload(self):
        self.timeout_checker.cancel()
        self._update_status_loop.stop()
        self.unpause_users.stop()
        
        
    @tasks.loop(hours = 24) # Check back every 24 hours
    async def _update_status_loop(self):
        """Updates the bot's status every 24 hours"""
        await self.update_status()
        

    @commands.guild_only()
    @commands.hybrid_command(name="join")
    async def add(self, ctx: commands.Context, public: bool = False):
        """Adds you to the list of authors"""
        guild_id = ctx.guild.id
        
        try:
            await self.user_manager.add_user(guild_id, ctx.author.id)
            await self.reply_to_message(context=ctx, content="Done!", ephemeral=not public)
            
            if(await self.user_manager.get_current_user(guild_id) == None):
                await self.file_manager.set_current_user_id(guild_id, ctx.author.id)
                await self.notify_people(guild_id)
                await self.file_manager.reset_timestamp(guild_id)
        except storybot_exceptions.UserIsBannedException:
            await self.reply_to_message(context=ctx, content="You are currently banned in this server. If you believe this is in error, please reach out to your server's moderators.", error=True, ephemeral=not public)
        except storybot_exceptions.AlreadyAnAuthorException:
            await self.reply_to_message(context=ctx, content="You are already an author in this server!", error=True, ephemeral=not public)

    @commands.guild_only()
    @commands.hybrid_command(name="leave")
    async def remove(self, ctx: commands.Context, public: bool = False):
        """Removes you from the list of authors"""
        
        proper_guild = self.get_proper_guild_id(ctx)
        
        await self.remove_user_plus_skip_logic(proper_guild, ctx.author.id)
        
        await self.reply_to_message(context=ctx, content="Done!", ephemeral=not public)


    @app_commands.guild_only()
    @app_commands.command(name="kick")
    #@app_commands.checks.has_permissions(moderate_members=True)
    async def kick(self, interaction: discord.Interaction, user: str, public: bool=False):
        """Admin command: kicks a user from the list of authors"""
        
        if not await self.is_moderator(interaction.user.id, interaction.channel):
            await self.reply_to_message(content=f"Only an admin can run this command!", interaction=interaction, error=True, ephemeral=not public)
            return
        
        try:
            user_id = await self.get_user_id_from_string(interaction.guild, user)
        except storybot_exceptions.UserNotFoundFromStringError:
            await self.reply_to_message(content="We couldn't find that user. Please try again!", interaction=interaction, error=True, ephemeral=not public)
            return
        
        proper_guild = self.get_proper_guild_id(interaction.channel)
        
        await self.remove_user_plus_skip_logic(proper_guild, user_id)
        
        await self.reply_to_message(content=f"<@{user_id}> has been kicked from StoryBot on this server (if he was an author).", interaction=interaction, ephemeral=not public)

    @app_commands.guild_only()
    @app_commands.command(name="ban")
    #@app_commands.checks.has_permissions(moderate_members=True)
    async def ban(self, interaction: discord.Interaction, user: str, public: bool = False):
        """Admin command: bans a user from joining the list of authors and kicks them if they're already there"""
        
        if not await self.is_moderator(interaction.user.id, interaction.channel):
            await self.reply_to_message(content=f"Only an admin can run this command!", interaction=interaction, error=True, ephemeral=not public)
            return
        
        try:
            user_id = await self.get_user_id_from_string(interaction.guild, user)
        except storybot_exceptions.UserNotFoundFromStringError:
            await self.reply_to_message(content="We couldn't find that user. Please try again!", interaction=interaction, error=True, ephemeral=not public)
            return
            
        if await self.is_moderator(user_id, interaction.channel) and not await self.config_manager.is_debug_mode():
            # await self.reply_to_message(content=f"Banning of moderators is not supported, as they could simply unban themselves. You can `/kick` a moderator, but not ban them.", interaction=interaction, error=True, ephemeral=True)
            # return
            pass
            
        if await self.user_manager.get_current_user(interaction.guild_id) == str(user_id):
            skip_after = True
        else:
            skip_after = False
        
        await self.file_manager.ban_user(guild_id=interaction.guild_id, user_id=user_id)
        
        if(skip_after):
            try:
                await self.new_user(interaction.guild_id)
            except ValueError:
                #This means that there's no users in the list of users. new_user will return an error but will also set the current user to None.
                pass
        
        await self.reply_to_message(content=f"<@{user_id}> has been banned from StoryBot on this server.", interaction=interaction, ephemeral=not public)

    @app_commands.guild_only()
    @app_commands.command(name="unban")
    #@app_commands.checks.has_permissions(moderate_members=True)
    async def unban(self, interaction: discord.Interaction, user: str, public: bool = False):
        """Admin command: unbans a user from joining the list of authors"""
        
        if not await self.is_moderator(interaction.user.id, interaction.channel):
            await self.reply_to_message(content=f"Only an admin can run this command!", interaction=interaction, error=True, ephemeral=not public)
            return
        
        try:
            user_id = await self.get_user_id_from_string(interaction.guild, user)
        except storybot_exceptions.UserNotFoundFromStringError:
            await self.reply_to_message(content="We couldn't find that user. Please try again!", interaction=interaction, error=True, ephemeral=not public)
            return
        
        await self.file_manager.unban_user(guild_id=interaction.guild_id, user_id=user_id)
        await self.reply_to_message(content=f"<@{user_id}> has been unbanned from StoryBot on this server (if he/she was banned).", interaction=interaction, ephemeral=not public)

    async def remove_user_plus_skip_logic(self, guild_id: int, user_id: int) -> None:
        """Removes a given user from the guild. If it's their turn, it skips to the next user

        Args:
            guild_id (int): the guild to remove the user from
            user_id (int): the user to remove from the guild
        """
        
        if await self.user_manager.get_current_user(guild_id) == await self.user_manager.get_current_user(guild_id):
            skip_after = True
        else:
            skip_after = False
        
        await self.user_manager.remove_user(guild_id, int(await self.user_manager.get_current_user(guild_id)))
    
        if(skip_after):
            try:
                await self.new_user(guild_id)
            except ValueError:
                #This means that there's no users in the list of users. new_user will return an error but will also set the current user to None.
                pass
        
    async def get_user_id_from_string(self, guild: discord.Guild, user: str) -> int:
        """Given a string used as a parameter in a command, returns a user. May return an invalid user id or throw a `storybot_exceptions.UserNotFoundFromStringError`"""
        user_object = None
        user_id = None
        
        try:
            user_object = await guild.fetch_member(int(re.sub(r'[^0-9]', '', user)))
        except (ValueError, discord.errors.NotFound):
            user_object = None
        
        if user_object == None:
            user_object = guild.get_member_named(user)
            
        if not user_object == None:
            return user_object.id
        
        try:
            user_id = int(re.sub(r'[^0-9]', '', user))
            if not (10000000000000000 <= user_id <= 18446744073709551615): # Make sure that the userid is valid (between `10^17` and `(2^64)-1`)
                raise storybot_exceptions.UserNotFoundFromStringError("The userID is not in the valid range!")
        except ValueError:
            # If the string ends up as '', this will run
            raise storybot_exceptions.UserNotFoundFromStringError()
        
        return user_id
            
        

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
        
        
    async def reply_to_message(self, message: discord.Message = None, content: str = "", context: commands.Context = None, file: discord.File = None, author_name: str = None, author_icon_url: str = None, title: str = None, ephemeral = True, view=None, interaction: discord.Interaction=None, error=False, followup=False) -> discord.Message:
        """Replies the given message

        Args:
            message (discord.abc.Messageable): the message or ctx to reply to
            content (str): the content to reply to
            file (discord.File): the file to embed (if one is needed)
            author (str): the user to display on the embed
        """
        
        if type(message) == "str":
            raise TypeError("`message` should be of type message, not a string! Maybe you meant to set `content`?")
        
        embed = await self.create_embed(content=content, title=title)
        
        if author_icon_url != None:
            embed.set_author(name=author_name, icon_url=author_icon_url)
            
        if error:
            embed.color = discord.Color.brand_red()
        
        try:
            if not context is None:
                return await context.send(embed = embed, file = file, mention_author = False, ephemeral=ephemeral, view=view)
            elif not message is None:
                return await message.reply(embed = embed, file = file, mention_author = False, view=view)
            elif not interaction is None:
                if followup == True:
                    eee = await interaction.followup.send(embed=embed) #, ephemeral=ephemeral)
                else:
                    try:
                        if view == None:
                            eee = await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
                        else:
                            eee = await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                    except discord.errors.NotFound:
                        await self.reply_to_message(embed=embed, view=view, ephemeral=ephemeral, interaction=interaction, followup=True)
                
                # if file == None:
                #     return await eee.send_message(embed=embed, view=view, ephemeral=True)
                # else:
                #     return await eee.send_message(embed=embed, view=view, ephemeral=True, file=file)
            else:
                raise ValueError("Both ctx and message passed to reply_to_message are None")
        except discord.errors.Forbidden:
            # TODO: Check for this perm properly
            pass
          
          
    async def new_user(self, guild_id: int, user_id: int = None):
        """Chooses a new user and notifies all relevant parties"""
        
        await self.file_manager.reset_timestamp(guild_id)
        if user_id == None:
            await self.user_manager.set_random_weighted_user(guild_id)
        else:
            if user_id in (await self.user_manager.get_active_and_inactive_users(guild_id)):
                await self.user_manager.set_current_user(guild_id=guild_id, user_id=user_id)
            else:
                raise storybot_exceptions.NotAnAuthorException(f"{user_id} is not an author in {guild_id}!")
        
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
            server_json.append({"id": guild_id, "name": guild_name})
        
        server_json.sort(key=lambda k: k["name"])
        
        view = DropdownView(server_json)
        
        my_message = await self.reply_to_message(message = message, content="Which server should this be added to?", view=view, ephemeral= True)
        
        await view.wait()
        
        await my_message.delete()
        
        return int(view.value)
    
    async def create_embed(self, content=None, color=None, title=None, author_name=None, author_icon_url=None) -> discord.Embed:
        """Creates an embed with the given parameters. All values have defaults if not given"""
        if color == None:
            color = await self.config_manager.get_embed_color()
        emb = discord.Embed(description=content, color=color, title=title)
        if author_name != None or author_icon_url != None:
            emb.set_author(name=author_name, icon_url=author_icon_url)
        
        return emb
    
    @commands.hybrid_command(name="my_turns")
    async def my_turns(self, ctx: commands.Context, public: bool = False):
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
            
        await self.reply_to_message(context=ctx, content=text, title=f"{ctx.author.name}'s current turns", ephemeral=not public)
        
    async def update_status(self):
        s=f" {len(await self.file_manager.get_all_guild_ids())} stories unfold"
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=s))
        print("Status updated to `watching" + s + "`")
        
        
        
    @app_commands.guild_only()
    @app_commands.command(name="configure")
    #@app_commands.checks.has_permissions(moderate_members=True)
    async def configure(self, interaction: discord.Interaction, setting: AvailableSettingsToModify, value: str = None, public: bool = False):
        """Admin command: change some of the bot's configuration"""
        if not await self.is_moderator(interaction.user.id, interaction.channel):
            await self.reply_to_message(content=f"Only an admin can run this command!", interaction=interaction, error=True, ephemeral=True)
            return
        
        proper_guild_id = self.get_proper_guild_id(interaction.channel)
        
        match setting:
            case AvailableSettingsToModify.StoryOutputChannel:
                if value == None:
                    new_story_output_channel = await self.choose_a_channel_in_a_server(guild_id=proper_guild_id, interaction=interaction, message="Choose a channel to output the story in!")
                    if new_story_output_channel == None: return
                    followup = True
                else:
                    new_story_output_channel = re.sub(r'[^0-9]', '', value)
                    if new_story_output_channel == '':
                        return
                    
                    new_story_output_channel = int(new_story_output_channel)
                    followup = False
                    
                    try:
                        channel = await interaction.guild.fetch_channel(new_story_output_channel)
                    except (discord.errors.Forbidden, discord.errors.NotFound):
                        await self.reply_to_message(content=f"Hmm... I can't see that channel for some reason. Check my permissions, then try again.", interaction=interaction, error=True, ephemeral=not public)
                        return
                    if not channel.permissions_for(await channel.guild.fetch_member(self.bot.user.id)).send_messages:
                        await self.reply_to_message(content=f"I can see that channel, but I can't send messages in it. Check my permissions, then try again.", interaction=interaction, error=True, ephemeral=not public)
                        return
                
                await self.file_manager.set_config_value(proper_guild_id, XSS_WARNING_config_name='story_output_channel', new_value=new_story_output_channel)
                await self.reply_to_message(content=f"Finished changing the story output channel to <#{new_story_output_channel}>!", interaction=interaction, followup=followup, ephemeral=not public)
            
            case AvailableSettingsToModify.AnnouncementChannel:
                if value == None:
                    new_story_announcement_channel = await self.choose_a_channel_in_a_server(guild_id=proper_guild_id, interaction=interaction, message="Choose a channel to announce the current user in!")
                    if new_story_announcement_channel == None: return
                    followup = True
                else:
                    new_story_announcement_channel = re.sub(r'[^0-9]', '', value)
                    if new_story_announcement_channel == '':
                        return
                    
                    new_story_announcement_channel = int(new_story_announcement_channel)
                    followup = False
                    
                    try:
                        channel = await interaction.guild.fetch_channel(new_story_announcement_channel)
                    except (discord.errors.Forbidden, discord.errors.NotFound):
                        await self.reply_to_message(content=f"Hmm... I can't see that channel for some reason. Check my permissions, then try again.", interaction=interaction, error=True, ephemeral=not public)
                        return
                    if not channel.permissions_for(await channel.guild.fetch_member(self.bot.user.id)).send_messages:
                        await self.reply_to_message(content=f"I can see that channel, but I can't send messages in it. Check my permissions, then try again.", interaction=interaction, error=True, ephemeral=not public)
                        return
                
                await self.file_manager.set_config_value(proper_guild_id, XSS_WARNING_config_name='story_announcement_channel', new_value=new_story_announcement_channel)
                await self.reply_to_message(content=f"Finished changing the story announcement channel to <#{new_story_announcement_channel}>!", interaction=interaction, followup=followup, ephemeral=not public)
            
            case AvailableSettingsToModify.TimeoutDays:
                try:
                    new_timeout_days=int(value)
                except ValueError:
                    # They didn't enter a number
                    await self.reply_to_message(content=f"Please enter a valid integer (whole number) for the `value`!", interaction=interaction, error=True, ephemeral=not public)
                    return
                except TypeError:
                    # They didn't enter anything
                    await self.reply_to_message(content=f"Please enter a number into the `value` field!", interaction=interaction, error=True, ephemeral=not public)
                    return
                
                max_timeout_days = await self.config_manager.get_max_timeout_days_configurable()
                
                if new_timeout_days <= 0:
                    await self.reply_to_message(content=f"Please choose a number of days greater than 0!", interaction=interaction, error=True, ephemeral=not public)
                    return
                elif max_timeout_days > 0 and new_timeout_days > max_timeout_days:
                    await self.reply_to_message(content=f"Timeout lengths greater than {max_timeout_days} are not supported by the bot right now. If you would like a longer timeout length, join my support server and let me know!", interaction=interaction, error=True, ephemeral=not public)
                    return
                
                await self.file_manager.set_config_value(proper_guild_id, XSS_WARNING_config_name='timeout_days', new_value=new_timeout_days)
                await self.reply_to_message(content=f"Finished setting the timeout days to **{new_timeout_days}**!", interaction=interaction, ephemeral=not public)
            
            case AvailableSettingsToModify.ResetCurrentPlayerTimeRemaining:
                await self.file_manager.reset_timestamp(proper_guild_id)
                await self.reply_to_message(content=f"Timestamp has been reset!", interaction=interaction, followup=False, ephemeral=not public)
            
            case AvailableSettingsToModify.SafeModeEnabled:
                yes_options = ["1", "yes", "true", "yep", "duh", "yes, please", "affirmative"]
                no_options = ["0", "no", "nah", "false", "no, thank you", "negative"]

                if value == None:
                    await self.reply_to_message(content="To toggle safe mode, please set the `value` of this command to either \"yes\" or \"no\". Thank you!", interaction=interaction, error=True, ephemeral=not public)
                    return
                value=value.lower()
                
                if value in yes_options:
                    activate = True
                elif value in no_options:
                    activate = False
                else:
                    await self.reply_to_message(content=f"I couldn't understand that. Please try again, and this time, set the `value` to \"yes\" or \"no\". Thanks!", interaction=interaction, error=True, ephemeral=not public)
                    return
                
                await self.file_manager.set_config_value(proper_guild_id, XSS_WARNING_config_name='safe_mode', new_value=activate)
                
                if activate:
                    message = "Safe Mode has been enabled. While it is still imperfect, it will help filter out some vulgarity in messages. This may be improved on in the future."
                else:
                    message = "**Warning: Safe Mode has been disabled**. Messages will *not* be filtered for vulgarity and the like."
                    
                await self.reply_to_message(content=message, interaction=interaction, ephemeral=not public)
                    
            
    async def is_moderator(self, user_id: int, guild_channel: discord.abc.GuildChannel):
        user = await guild_channel.guild.fetch_member(user_id)
        if user == None:
            print(f"No user found: {user_id} {guild_channel}")
            return False
        return guild_channel.permissions_for(user).moderate_members
            
                
    async def choose_a_channel_in_a_server(self, guild_id: int, interaction: discord.Interaction, message=None) -> int:
        server_json = []
        self_member = self.bot.get_guild(guild_id).get_member(self.bot.user.id)
        
        for channel in self.bot.get_guild(guild_id).text_channels:
            if channel.permissions_for(self_member).send_messages == True:
                server_json.append({"id": channel.id, "name": channel.name})
        
        server_json.append({"id": -1, "name": "<Disabled>"})
        server_json.append({"id": 0, "name": "<Cancel>"})
        
        view = DropdownView(server_json, "Choose a channel")
        
        if message == None:
            message = "Which channel would you like to choose?"
        
        my_message = await self.reply_to_message(interaction=interaction, content=message, view=view, ephemeral= True)
        
        await view.wait()
        
        await interaction.delete_original_response()
        
        if view.value == None:
            return None
        else:
            return int(view.value)

    @app_commands.guild_only()
    @app_commands.command(name="archive_story", description="Admin command: archives your current story and starts a new story")
    @app_commands.checks.cooldown(1, 24 * 60 * 60) # Makes sure this can only be run once a day
    #@app_commands.checks.has_permissions(moderate_members=True)
    async def new_story(self, interaction: discord.Interaction, confirm: bool, delete_old_story:bool = False, public: bool = False):
        
        if not confirm:
            await self.reply_to_message(content=f"Just to be sure no one accidentally types this command, you need to set the `confirm` parameter to True to create a new story. If that was your goal, try running this command again with that parameter changed. If not, feel free to ignore this!", interaction=interaction, ephemeral=not public)
            return
            
        if not await self.is_moderator(interaction.user.id, interaction.channel):
            await self.reply_to_message(content=f"Only an admin can run this command!", interaction=interaction, error=True, ephemeral=not public)
            return
        
        try:
            await self.file_manager.new_story(interaction.guild_id, forced = delete_old_story)
            await self.reply_to_message(content=f"Your old story has been archived, and a new story has been created! Run `/story {await self.file_manager.get_archived_story_count(interaction.guild_id)}` to see your last story, and feel free to start your storywriting. Have fun!", interaction=interaction, ephemeral=not public)
            await self.new_user(guild_id=interaction.guild_id)
            
        except storybot_exceptions.TooManyArchivedStoriesException:
            await self.reply_to_message(content=f"Unfortunately, you've reached the limit for stories archived, {await self.file_manager.get_archived_story_count(interaction.guild_id)}. If you'd like to delete your first stored story, you can replace it with this story. Make sure to set the `delete_old_story` tag to true, then run this command again.\n\nYou can run `/story 1` and pin that message before resetting the story to make sure everyone still has access to it; I just need to make sure I have enough space on my hard drive to store everyone's stories. Thanks for understanding!\n\nIf you have any questions or complaints, feel free to bring them up in my Discord server! The link is in my bio.", interaction=interaction, ephemeral=not public)
            
    @app_commands.guild_only()
    @app_commands.command(name="current_users")
    async def list_users(self, interaction: discord.Interaction, public: bool = False):
        """Lists the active users in a guild"""
        
        gid = self.get_proper_guild_id(interaction.channel)
        
        list_of_ids = await self.user_manager.get_unweighted_list(gid)
        
        if len(list_of_ids) == 0:
            response = "There are no active users in this server. Join the bot to become the first!"
        else:
            response = ""
            for id in list_of_ids:
                response += f"<@!{id}>\n"
            response = response.rstrip()
        
        await self.reply_to_message(interaction=interaction, content=response, title="Current authors in this guild", ephemeral=not public)
        
    async def purge_guild_id_list(self):
        """Checks which guilds the bot is not in and leaves those guilds"""
        
        print("Starting purge")
        
        for guild_id in await self.file_manager.get_all_guild_ids():
            try:
                if await self.bot.fetch_guild(guild_id) == None:
                    raise storybot_exceptions.NotInGuildException
            except (discord.errors.NotFound, discord.errors.Forbidden, storybot_exceptions.NotInGuildException):
                print(f"Not in guild {guild_id} - leaving")
                await self.file_manager.remove_guild(guild_id)
                
        print("Finished purge")
    
    @app_commands.guild_only()
    @app_commands.command(name="undo")
    #@app_commands.checks.has_permissions(moderate_members=True)
    async def undo(self, interaction: discord.Interaction, public: bool = False):
        """Admin command: deletes the last message added to the bot"""
        if not await self.is_moderator(interaction.user.id, interaction.channel):
            await self.reply_to_message(content=f"Only an admin can run this command!", interaction=interaction, error=True, ephemeral=not public)
            return
        
        proper_guild_id = self.get_proper_guild_id(interaction.channel)
        
        try:
            message_number = await self.file_manager.undo_last_chunk(proper_guild_id)
            
            await self.reply_to_message(interaction=interaction, content="Deleted the last addition to the story!", ephemeral=not public)
        
        except storybot_exceptions.NoValidUndoCommand as e:
            await self.reply_to_message(interaction=interaction, content=f"Something went wrong undoing the last message. {str(e)}", error=True, ephemeral=not public)


    @app_commands.guild_only()
    @app_commands.command(name="set_turn")
    #@app_commands.checks.has_permissions(moderate_members=True)
    async def set_turn(self, interaction: discord.Interaction, user: str, public: bool = False):
        """Admin command: Sets the current user for the bot"""
        
        if not await self.is_moderator(interaction.user.id, interaction.channel):
            await self.reply_to_message(content=f"Only an admin can run this command!", interaction=interaction, error=not public, ephemeral=True)
            return
        
        try:
            user_id = await self.get_user_id_from_string(interaction.guild, user)
        except storybot_exceptions.UserNotFoundFromStringError:
            await self.reply_to_message(content="We couldn't find that user. Please try again!", interaction=interaction, error=not public)
            return
        
        proper_guild = self.get_proper_guild_id(interaction.channel)
        
        try:
            await self.new_user(guild_id=proper_guild, user_id=user_id)
            await self.reply_to_message(interaction=interaction, content=f"Done! It is now <@!{user_id}>'s turn.", ephemeral=not public)
        except storybot_exceptions.NotAnAuthorException:
            if user_id == self.bot.user.id:
                await self.reply_to_message(interaction=interaction, content=f"I'd love to, but unfortunately, I can't write (yet). Maybe try in a year or so, or keep up-to-date in our support server!", error=True, ephemeral=not public)
            else:
                await self.reply_to_message(interaction=interaction, content=f"<@!{user_id}> is not an author in this guild. Have them run `/join`, then try again.", error=True, ephemeral=not public)
        
    @app_commands.guild_only()
    @app_commands.command(name="pause")
    async def pause(self, interaction: discord.Interaction, days: int = 0, weeks: int = 0, public: bool = False):
        """Pauses your turn for the length of time requested"""
        error_message = None
        
        if days < 0:
            await self.reply_to_message(interaction=interaction, content=f"Please enter a positive number of days to pause for!", error=True, ephemeral=not public)
            return
        if weeks < 0:
            await self.reply_to_message(interaction=interaction, content=f"Please enter a positive number of weeks to pause for!", error=True, ephemeral=not public)
            return
        if days + weeks * 7 > 90:
            await self.reply_to_message(interaction=interaction, content=f"You can only pause for up to 90 days. Please try again!", error=True, ephemeral=not public)
            return
        
        if str(interaction.user.id) == await self.user_manager.get_current_user(interaction.guild_id):
            skip_after = True
            print("Skip!")
        else:
            skip_after = False
            print("Don't skip!")
        
        try:
            await self.user_manager.pause_user(guild_id=interaction.guild_id, user_id=interaction.user.id, days=days + weeks * 7)
        except storybot_exceptions.NotAnAuthorException:
            await self.reply_to_message(interaction=interaction, content=f"You have to be an author to pause your turn!", error=True, ephemeral=not public)
            return
        
        if(skip_after):
            try:
                await self.new_user(interaction.guild_id)
            except ValueError:
                #This means that there's no users in the list of users. new_user will return an error but will also set the current user to None.
                pass
        
        if days + weeks * 7 == 0:
            await self.reply_to_message(interaction=interaction, content=f"Success! You are now paused until you run `/join` again.", ephemeral=not public)
        else:
            await self.reply_to_message(interaction=interaction, content=f"Success! You are now paused for {days + weeks * 7} days!\n\nTo rejoin early, run `/join` again.", ephemeral=not public)
        
        
        
class DropdownView(discord.ui.View):
    def __init__(self, server_json, dropdown_placeholder='Which server is this story for?'):
        super().__init__()

        # Adds the dropdown to our view object.
        self.add_item(ServerChooser(server_json, self, dropdown_placeholder))
        self.guild_id = None
        self.value = None

class ServerChooser(discord.ui.Select):
    def __init__(self, guild_json, view, dropdown_placeholder):
        guilds = []

        for item in guild_json:
            option = discord.SelectOption(label=item["name"],
                                          value=item["id"])
            
            guilds.append(option)
            
        self.vv = view
        super().__init__(placeholder=dropdown_placeholder, min_values=1, max_values=1, options=guilds)
        
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
        """End a string with a period if other punctuation is missing"""
        
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

def pieMethod(story):
    """The all-powerful pieMethod
    Splits the story into a list of strings if it is too long"""
    MAX_MESSAGE_LENGTH = 1950
    if len(story) <= MAX_MESSAGE_LENGTH:
        return [story]
    list = []
    count = math.ceil(len(story) / MAX_MESSAGE_LENGTH)
    for i in range(0, count):
        if i == count:
            text = story[i*MAX_MESSAGE_LENGTH:]
        else:
            text = story[i*MAX_MESSAGE_LENGTH:(i+1)*MAX_MESSAGE_LENGTH]
        
        if text.strip() != "":
            list.append(text)
    return list