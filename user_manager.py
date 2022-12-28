import random
from config_manager import ConfigManager
from file_manager import file_manager

class user_manager():
    def __init__(self, bot, config_manager: ConfigManager):
        self.bot = bot
        self.config_manager: ConfigManager = config_manager
    
    async def set_random_weighted_user(self, guild_id: int) -> int:
        """Sets a random user as the current user based on their reputation"""
        json_formatted = await self.bot.file_manager.get_active_users_and_reputations(guild_id)
        ids = []
        reputations = []
        for key in json_formatted.keys():
            if await self.is_recent_user(guild_id, int(key)):
                continue
            ids.append(key)
            reputations.append(json_formatted[key])
        
        if(len(ids)) == 0:
            new_user = None
        else:
            new_user = int(random.choices(ids, weights=reputations)[0])
        
        await self.set_current_user(guild_id, new_user)
        
        return new_user

    async def set_random_unweighted_user(self, guild_id: int) -> int:
        """Sets a random user as the current user. Doesn't care about reputation."""
        unweighted_list = await self.get_unweighted_list(guild_id)
        
        for id in await self.get_recent_users_queue(guild_id):
            unweighted_list.remove(id)
        
        if(len(unweighted_list)) == 0:
            new_user = None
        else:
            new_user = int(random.choice(unweighted_list))
        
        await self.set_current_user(guild_id, new_user)
        
        return new_user

    async def set_current_user(self, guild_id: int, user_id: int):
        await self.bot.file_manager.set_current_user_id(guild_id, user_id)

    async def get_current_user(self, guild_id: int) -> str:
        """Returns the current user's id as a string"""
        ret = await self.bot.file_manager.get_current_user_id(guild_id)
        if ret == "" or ret == "0":
            return None
        else:
            return ret

    async def add_user(self, guild_id: int, user_id):
        """Adds the given user to the list of users"""
        await self.bot.file_manager.add_user(user_id=user_id, guild_id=guild_id)

    async def remove_user(self, guild_id: int, user_id: int):
        """Removes the given user from the list of users"""
        await self.bot.file_manager.remove_user(user_id=user_id, guild_id=guild_id)

    async def boost_user(self, guild_id: int, user_id):
        """Boosts the given user's reputation"""
        
        await self.bot.file_manager.alter_reputation(user_id=user_id, guild_id=guild_id, amount=1)
        
    async def unboost_user(self, guild_id: int, user_id):
        """Reduces the given user's reputation"""
        
        await self.bot.file_manager.alter_reputation(user_id=user_id, guild_id=guild_id, amount=-1)

    async def get_weighted_list(self, guild_id: int) -> list[int]:
        return await self.bot.file_manager.get_weighted_list_of_users(guild_id)

    async def get_unweighted_list(self, guild_id: int) -> list[int]:
        return await self.bot.file_manager.get_active_users(guild_id)


    ######################################
    # The methods for the recent users queue.
    # These should probably be in their own class, but since this implementation may be changing when multi server support is added, I decided to just put them in here for now.
    ######################################

    async def get_recent_users_queue(self, guild_id: int) -> list[int]:
        return await self.bot.file_manager.get_recent_users_queue(guild_id)

        
    async def is_recent_user(self, guild_id: int, user_id: int) -> bool:
        """Returns if a user is in the list of recent users

        Args:
            guild_id (int): the guild to check for the user in
            user_id (int): the user id to check

        Returns:
            bool: whether the user is a recent user
        """
        return user_id in await self.get_recent_users_queue(guild_id)
    
    async def pause_user(self, guild_id: int, user_id: int, days: int = 0):
        await self.bot.file_manager.pause_user(guild_id, user_id, days)

    async def unpause_all_necessary_users(self) -> list:
        print("Checking for unpauses...")
        list_to_unpause = await self.bot.file_manager.get_all_users_to_unpause()
        for tup in list_to_unpause:
            print(f"unpausing {tup}")
            await self.bot.file_manager.make_user_active(tup[0], tup[1])
        return list_to_unpause


@staticmethod
def remove_all_occurrences(given_list:list, item) -> list:
    """Removes all occurrences of an item from a given list

    Args:
        given_list (list): the list to remove the item from
        item: the item to remove

    Returns:
        list: the list without the item in it
    """
    given_list = given_list.copy()
    while(item in given_list):
        given_list.remove(item)
    return given_list
