import discord
import math
import asyncio
import time
import os
import collections
import json
from discord.ext import tasks, commands

class dmlistener(commands.Cog):
    def __init__(self, file_manager, user_manager, bot):
        self.file_manager = file_manager
        self.user_manager = user_manager
        self.current_user = int(user_manager.get_current_user())
        self.bot = bot
        self.messageNotSent = False
        self.timeout_checker.start()
        self.last_checked_user = self.current_user
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

    async def dm_current_user(self, message, file = None):
        await (await self.bot.get_user(int(self.user_manager.get_current_user())).create_dm()).send(message, file = file)

        
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


    @commands.command()
    async def story(self, ctx, *parameters):
        try:
            if parameters[-1].isdigit():
                print('Digit found!')
                file = discord.File("story {0}.txt".format(int(parameters[-1])), filename="story {0}.txt".format(int(parameters[-1])))
                await ctx.send('Here is story {0}:'.format(int(parameters[-1])), file = file)
            else:
                print('No digit found!')
                raise Exception('')
        except:
            file = discord.File("story.txt", filename="story.txt")
            await ctx.send("```"+self.lastChars(self.file_manager.getStory())+"```", file = file)
   
    @commands.is_owner()
    @commands.command()
    async def push(self, ctx):
        import os, time
        os.system("git commit -am \"{0}\"".format(time.time()))
        os.system("git pull")
        os.system("git push")
        await ctx.send("oki swine it done")
    
    @commands.command()
    async def turn(self, ctx):
        await ctx.send("It is currently " + self.bot.get_user(int(self.user_manager.get_current_user())).display_name + "'s turn!")

    @commands.command()
    async def help(self, ctx):
        await ctx.send(
            """This bot is a story bot.  One user will write a part of the story (anywhere from a sentence or two to a couple of paragraphs - your choice!), then another, and so on until the story is complete!
            
    `s.add` adds you to the authors, while `s.remove` removes you
    `s.story` displays the story so far - put a number afterwards to see a past story
    `s.turn` displays whose turn it is""")

    @commands.command()
    async def skip(self, ctx):
        if str(ctx.author.id) != self.user_manager.get_current_user() and ctx.author.id != 351804839820525570:
            return await ctx.send("It's not your turn!")
        await ctx.send("Skipping :(")
        self.current_user = self.user_manager.get_random_weighted_user()

        await self.notify_people()
        await self.wait_and_check()

    @commands.command()
    async def notify(self, ctx):
        await self.notify_people()

    @commands.is_owner()
    @commands.command()
    async def list_users(self, ctx):
        print(self.user_manager.get_list())

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

    def lastChars(self, story):
        return story[len(story) -1500:len(story) -1]


    async def wait_and_check(self):
        return
        def check(message):
            return str(message.author.id) == self.user_manager.get_current_user()

        try:
            message2, user = await self.bot.wait_for('on_message', timeout = 60*60*24, check = check)
        except asyncio.TimeoutError:
            await timeout_happened()

    async def timeout_happened(self):
        print('about to dm') 
        try:
            await self.dm_current_user('You took too long!  You\'ll have a chance to add to the story later - don\'t worry!')
            print('dmed.  About to unboost...')
        except:
            print('failed to DM.  Moving on...')
        self.user_manager.unboost_user(self.current_user)
        print('unboosted.  About to change current user......') 
        self.current_user = self.user_manager.get_random_weighted_user()
        print('done!')
        await self.notify_people()

        self.last_checked_user = self.current_user
        self.timestamp = time.time()
        os.remove('timestamp.txt')
        with open('timestamp.txt', 'w') as f:
            f.write(str(self.timestamp))

    @tasks.loop(seconds=60 * 60) # 60 minutes
    async def timeout_checker(self):
        if self.last_checked_user is self.current_user: #still the same person
            if time.time() - self.timestamp >= 60 * 60 * 24: # if the time is over 24 hours
                print('about to timeout')
                await self.timeout_happened()
                print('timeout happened')

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


    @commands.command()
    async def add(self, ctx):
        self.user_manager.add_user(ctx.author.id)
        await ctx.send("Done!")

    @commands.command()
    async def remove(self, ctx):
        self.user_manager.remove_user(ctx.author.id)
        await ctx.send("Done!")

    @commands.is_owner()
    @commands.command()
    async def newstory(self, ctx):
        #TODO: finish it
        await ctx.send("This command isn't ready yet!")
        #self.file_manager.new_story()
        #await ctx.send("Done!")

    @commands.is_owner()
    @commands.command(aliases = ['rep'])
    async def reputation(self, ctx, mentn : discord.Member = None):
        if mentn == None:
            ID = int(ctx.author.id)
        else:
            ID = int(mentn.id)

        print(collections.Counter(self.user_manager.get_list()))

        await ctx.send(collections.Counter(self.user_manager.get_list())[ID])

    @commands.is_owner()
    @commands.command(aliases = ['lsrep', 'listrep'])
    async def listreputation(self, ctx):
        s = ''
        for item in collections.Counter(self.user_manager.get_list()).keys():
            s += self.bot.get_user(item).name + ': ' + str(collections.Counter(self.user_manager.get_list())[item]) + '\n'
        await ctx.send(s)
        
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