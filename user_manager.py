import secrets
import os
import collections
import json
import config_manager

class user_manager():
    def __init__(self, bot):
        self.bot = bot
        
        # Create the initial list of users 
        try:
            with open('weighted list of users.json', 'rt') as f:
                self.weighted_list_of_users = json.load(f)
            # TODO: make sure no user is in the list too often
        except:
            self.weighted_list_of_users = []
            for item in config_manager.get_default_user_ids():
                self.add_user(config_manager.get_default_guild_id(), item)
            self.serialize()
                
                
        # Create the recent queue
        try:
            with open('recent_users.json', 'rt') as f:
                self.recent_users = json.load(f)
            # TODO: check if any user is in the list of recent users more often than the maximum
        except:
            self.recent_users = []
            self.serialize_queue()
        
    
    def set_random_weighted_user(self, guild_id: int, add_last_user_to_queue = True) -> int:
        """Sets a random user as the current user based on their reputation"""
        if add_last_user_to_queue:
            self.add_to_recent_users_queue(guild_id, int(user_manager.get_current_user(guild_id)))
        
        return self.__set_new_random_user(self.get_weighted_list(guild_id), guild_id)

    def set_random_unweighted_user(self, guild_id: int, add_last_user_to_queue = True) -> int:
        """Sets a random user as the current user. Doesn't care about reputation."""
        if add_last_user_to_queue:
            self.add_to_recent_users_queue(guild_id, int(user_manager.get_current_user(guild_id)))
            
        return self.__set_new_random_user(self.get_unweighted_list(guild_id), guild_id)
    
    
    def __set_new_random_user(self, listToChooseFrom:list, guild_id = int) -> int:
        """Sets a random user from the list as the current user

        Args:
            listToChooseFrom (list): the list to choose a random user from

        Raises:
            ValueError: the list passed to the function doesn't have any members
        
        Returns:
            int: the random user now set as the current user
        """
        
        if len(listToChooseFrom) == 0:
            raise ValueError("No users passed to `__set_new_random_user`")
        
        internalListToChooseFrom = listToChooseFrom

        if config_manager.get_amount_to_not_repeat() > 0:
            # Makes sure the same user isn't chosen more than once in a row, even if the most recent user wasn't added to the queue (like in a skip)
            internalListToChooseFrom = user_manager.remove_all_occurrences(internalListToChooseFrom, user_manager.get_current_user(guild_id))
                
            # Makes sure that the chosen user isn't in the recent users queue
            for item in self.get_recent_users_queue(guild_id):
                internalListToChooseFrom = user_manager.remove_all_occurrences(internalListToChooseFrom, item)
            
        
        # If there's too many people on the recent user queue, pop the most recent and try again. That way, it'll go in sequential order
        if(len(internalListToChooseFrom) < 1):
            self.pop_from_recent_users_queue(guild_id)
            return self.__set_new_random_user(listToChooseFrom, guild_id)
        
        new_user = secrets.choice(internalListToChooseFrom)
        
        os.remove("user.txt")
        with open('user.txt', 'w') as f:
            f.write(str(new_user))
        
        return new_user



    @staticmethod
    def get_current_user(guild_id: int) -> str:
        """Returns the current user"""
        file = open("user.txt", "r")
        currentUserID = file.read()
        file.close()
        return currentUserID

    def add_user(self, guild_id: int, user_id):
        """Adds the given user to the list of users"""
        if user_id not in self.get_weighted_list(guild_id):
            for i in range(0, config_manager.get_default_reputation(guild_id)):
                self.weighted_list_of_users.append(user_id)
        self.serialize()

    def remove_user(self, guild_id: int, user_id):
        """Removes the given user from the list of users"""
        for i in range(0, collections.Counter(self.weighted_list_of_users)[user_id]):
            self.weighted_list_of_users.remove(user_id)
        self.serialize()

    def boost_user(self, guild_id: int, user_id):
        """Boosts the given user's reputation"""
        if(collections.Counter(self.weighted_list_of_users)[user_id] < config_manager.get_max_reputation(user_id)):
            self.weighted_list_of_users.append(user_id)
        self.serialize()
        print('boosted {0} finished'.format(user_id))

    def unboost_user(self, guild_id: int, user_id):
        """Reduces the given user's reputation"""
        if(collections.Counter(self.weighted_list_of_users)[user_id] > 2):
            self.weighted_list_of_users.remove(user_id)
        self.serialize()
        print('unboosted {0} successful'.format(user_id))

    def get_weighted_list(self, guild_id: int):
        return self.weighted_list_of_users

    def get_unweighted_list(self, guild_id: int):
        return set(self.weighted_list_of_users)


    ######################################
    # The methods for the recent users queue.
    # These should probably be in their own class, but since this implementation may be changing when multi server support is added, I decided to just put them in here for now.
    ######################################
    
    def pop_from_recent_users_queue(self, guild_id: int) -> None:
        """Removes the first user from the list of recent users"""
        try:
            self.recent_users.pop(0)
        except IndexError:
            pass
        self.serialize_queue()
        
    def add_to_recent_users_queue(self, guild_id: int, user_id: int) -> None:
        """Adds a given user ID to the list of recent users. Pops the first user if the list's length is longer than `LAST_N_PLAYERS_NO_REPEAT`

        Args:
            id (int): the user ID to add to the recent user queue
        """
        self.recent_users.append(user_id)
        
        if(self.recent_users_queue_size(guild_id) > config_manager.get_amount_to_not_repeat()):
            while(self.recent_users_queue_size(guild_id) > config_manager.get_amount_to_not_repeat()):
                self.pop_from_recent_users_queue(guild_id)
        
            # There's no need to serialize here since pop_recent_queue() serializes automatically
        else:
            self.serialize_queue()
            
            
    def recent_users_queue_size(self, guild_id: int) -> int:
        """Returns the size of the list of recent users"""
        return len(self.recent_users)
            
    def is_recent_user(self, guild_id: int, user_id: int) -> bool:
        """Returns if a user is in the list of recent users

        Args:
            user_id (int): the user id to check

        Returns:
            bool: whether the user is a recent user
        """
        
        return user_id in self.recent_users
    
    def get_recent_users_queue(self, guild_id: int) -> list:
        return self.recent_users
    
    
    
        
    def serialize(self):
        with open('weighted list of users.json', 'w') as f:
            json.dump(self.weighted_list_of_users, f, indent=4)
        
    def serialize_queue(self):
        with open('recent_users.json', 'w') as f:
            json.dump(self.recent_users, f, indent=4)




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
