import discord
import math
import asyncio
import time
import os
import collections
import json
from discord.ext import tasks, commands

# Listens for DMs to add to the story
class dmlistener(commands.Cog):
    def __init__(self, file_manager, user_manager, bot):
        self.file_manager = file_manager
        self.user_manager = user_manager
        
        # Keeps track of the current user's id
        self.current_user = int(user_manager.get_current_user())
        
        self.bot = bot
        self.messageNotSent = False
        self.timeout_checker.start()
        self.last_checked_user = self.current_user
        
        # The timestamp keeps track of when the last user was notified, so that even if the bot goes down, it still knows how much longer the current user has to continue the story
        try:
            timestamp_file = open("timestamp.txt", "r")
            self.timestamp = float(timestamp_file.read())
            timestamp_file.close()
        except:
            self.timestamp = time.time()

        try:
            os.remove('timestamp.txt')
        except:
            1
        
        with open('timestamp.txt', 'w') as f:
            f.write(str(self.timestamp))

    # Sends the given message to the current user
    async def dm_current_user(self, message, file = None):
        await (await self.bot.get_user(int(self.user_manager.get_current_user())).create_dm()).send(message, file = file)

    # Notifies the current user that it's their turn to add to the story
    async def notify_people(self):
        file = discord.File("story.txt", filename="story.txt")
        await self.dm_current_user("""Your turn.  Respond with a DM to continue the story!  Use a \ to create a line break.
            
            **MAKE SURE THE BOT IS ONLINE BEFORE RESPONDING!**  You will get a confirmation response if your story is received.
            
            Here is the story so far:
            ```{0}```""".format(self.lastChars(self.file_manager.getStory()))
            , file = file)
        
        # Send a message in the story chanel
        await self.bot.get_channel(611949797733302292).send("It's now {0}'s turn!".format(self.bot.get_user(int(self.user_manager.get_current_user())).name))
        
        # DM me the new user
        #await (await self.bot.get_user(351804839820525570).create_dm()).send(self.bot.get_user(int(self.user_manager.get_current_user())).name + ", " + self.bot.get_user(int(self.user_manager.get_current_user())).mention)

    # Returns the requested story
    # If there is a number, the given story number will be returned
    @commands.command()
    async def story(self, ctx, *parameters):
        try:
            if parameters[-1].isdigit():
                print('Story requested. Correct digit found!')
                file = discord.File("story {0}.txt".format(int(parameters[-1])), filename="story {0}.txt".format(int(parameters[-1])))
                await ctx.send('Here is story {0}:'.format(int(parameters[-1])), file = file)
            else:
                print('Story requested. No digit found!')
                raise Exception('')
        except:
            file = discord.File("story.txt", filename="story.txt")
            await ctx.send("```"+self.lastChars(self.file_manager.getStory())+"```", file = file)
   
    # Syncs the story with the old git repo
    # Will need to be removed
    @commands.is_owner()
    @commands.command()
    async def push(self, ctx):
        import os, time
        os.system("git commit -am \"{0}\"".format(time.time()))
        os.system("git pull")
        os.system("git push")
        await ctx.send("oki swine it done")
    
    # Sends a message with the current user's name
    @commands.command()
    async def turn(self, ctx):
        await ctx.send("It is currently " + self.bot.get_user(int(self.user_manager.get_current_user())).display_name + "'s turn!")

    # The help command
    @commands.command()
    async def help(self, ctx):
        await ctx.send(
            """This bot is a story bot.  One user will write a part of the story (anywhere from a sentence or two to a couple of paragraphs - your choice!), then another, and so on until the story is complete!
            
    `s.add` adds you to the authors, while `s.remove` removes you
    `s.story` displays the story so far - put a number afterwards to see a past story
    `s.turn` displays whose turn it is""")

    # Skips the current user
    @commands.command()
    async def skip(self, ctx):
        if str(ctx.author.id) != self.user_manager.get_current_user() and ctx.author.id != 351804839820525570:
            return await ctx.send("It's not your turn!")
        await ctx.send("Skipping :(")
        self.current_user = self.user_manager.get_random_weighted_user()

        await self.notify_people()
        await self.wait_and_check()

    # The command to notify users that it's their turn
    @commands.command()
    async def notify(self, ctx):
        await self.notify_people()

    # Lists the users working on the story
    @commands.is_owner()
    @commands.command()
    async def list_users(self, ctx):
        print("\nList of users:\n" + self.user_manager.get_list())

    # Checks if the message is the story, and if it is, appends it
    @commands.Cog.listener()
    async def on_message(self, message):
        if self.messageNotSent:
            file = discord.File("story.txt", filename="story.txt")
            await self.notify_people()
            self.messageNotSent = False

        if message.guild is None:
            if self.user_manager.get_current_user() == str(message.author.id):
                if "s.skip" in message.content:
                    return
                self.file_manager.addLine(message.content)
                self.user_manager.boost_user(self.current_user)
                self.current_user = self.user_manager.get_random_user()
                await message.channel.send("Got it!  Thanks!")

                await self.notify_people()
                await self.wait_and_check()

    # The all-powerful pieMethod
    # Splits the story into a list of strings if it is too long
    def pieMethod(self, story):
        if len(story) >= 1500:
            split = list()
            for i in range(math.ceil(len(story) / 1500)):
                if i == math.ceil(len(story) / 1500):
                    split.append(story[i:len(story) -1])
                else:
                    split.append(story[i:i+1500])
            return split
        else:
            return story

    # Returns the last 1500 characters of the story
    def lastChars(self, story):
        return story[len(story) -1500:len(story) -1]

    # Should wait for 24 hours, then skip the current user's turn
    async def wait_and_check(self):
        return
        def check(message):
            return str(message.author.id) == self.user_manager.get_current_user()

        try:
            message2, user = await self.bot.wait_for('on_message', timeout = 60*60*24, check = check)
        except asyncio.TimeoutError:
            await timeout_happened()

    # Skips the current user's turn if they don't respond in 24 hours
    async def timeout_happened(self):
        print('about to dm '+str(self.current_user) + ' that they have been skipped due to taking too long') 
        try:
            await self.dm_current_user('You took too long!  You\'ll have a chance to add to the story later - don\'t worry!')
            print('skip dm to '+str(self.current_user)+' successful.  About to unboost...')
        except:
            print('failed to DM '+str(self.current_user)+'.  Moving on...')
        self.user_manager.unboost_user(self.current_user)
        print('unboosted '+str(self.current_user)+'.  About to change current user......') 
        self.current_user = self.user_manager.get_random_weighted_user()
        print('done unboosting '+str(self.current_user)+'!')
        await self.notify_people()

        self.last_checked_user = self.current_user
        self.timestamp = time.time()
        os.remove('timestamp.txt')
        with open('timestamp.txt', 'w') as f:
            f.write(str(self.timestamp))

    # SHOULD skip the current user's turn if they don't respond in 24 hours
    @tasks.loop(seconds=60 * 60) # 60 minutes
    async def timeout_checker(self):
        if self.last_checked_user is self.current_user: #still the same person
            if time.time() - self.timestamp >= 60 * 60 * 24: # if the time is over 24 hours
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

        #time.time() returns an double of seconds

    def cog_unload(self):
        self.timeout_checker.cancel()

    # Adds a user to the list of participants
    @commands.command()
    async def add(self, ctx):
        self.user_manager.add_user(ctx.author.id)
        await ctx.send("Done!")

    # Removes a user from the list of participants
    @commands.command()
    async def remove(self, ctx):
        self.user_manager.remove_user(ctx.author.id)
        await ctx.send("Done!")

    # Should be used at the end of a story to create a new story
    @commands.is_owner()
    @commands.command()
    async def newstory(self, ctx):
        #TODO: finish it
        await ctx.send("This command isn't ready yet!")
        #self.file_manager.new_story()
        #await ctx.send("Done!")

    # Gives the reputation of a current user
    @commands.is_owner()
    @commands.command(aliases = ['rep'])
    async def reputation(self, ctx, mentn : discord.Member = None):
        if mentn == None:
            ID = int(ctx.author.id)
        else:
            ID = int(mentn.id)

        print('listing reputations:\n'+collections.Counter(self.user_manager.get_list()))

        await ctx.send(collections.Counter(self.user_manager.get_list())[ID])

    # Lists all users' reputations along with their names
    @commands.is_owner()
    @commands.command(aliases = ['lsrep', 'listrep'])
    async def listreputation(self, ctx):
        s = ''
        for item in collections.Counter(self.user_manager.get_list()).keys():
            s += self.bot.get_user(item).name + ': ' + str(collections.Counter(self.user_manager.get_list())[item]) + '\n'
        await ctx.send(s)
        
    # Boosts a user's reputation
    @commands.is_owner()
    @commands.command(aliases = [])
    async def boost(self, ctx, mentn : discord.Member = None):
        return
        if mentn == None:
            ID = int(ctx.author.id)
        else:
            ID = int(mentn.id)

        self.user_manager.boost_user(id)
            
        await ctx.send(f"Boosted <@!{ID}>!")
        
    # Unboosts a user's reputation
    @commands.is_owner()
    @commands.command(aliases = [])
    async def unboost(self, ctx, mentn : discord.Member = None):
        return
        if mentn == None:
            ID = int(ctx.author.id)
        else:
            ID = int(mentn.id)

        self.user_manager.boost_user(id)
            
        await ctx.send(f"Unboosted <@!{ID}>!")

    

if __name__ == '__main__':
    import main