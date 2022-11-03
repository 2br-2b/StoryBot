import secrets
import os
import config
import collections
import json

class user_manager():
    def __init__(self, bot):
        self.bot = bot
        
        # Create the initial list of users
        try:
            with open('weighted list of users.json', 'rt') as f:
                self.weighted_list_of_users = json.load(f)
            for id in self.weighted_list_of_users:
                while(collections.Counter(self.weighted_list_of_users)[id] > config.MAX_REPUTATION):
                    self.unboost_user(id)
        except:
            self.weighted_list_of_users = []
            for item in config.DEFAULT_USER_IDS:
                self.add_user(item)
        
    
    def set_random_weighted_user(self) -> int:
        """Sets a random user as the current user based on their reputation"""
        return self.__set_new_random_user(self.get_weighted_list())

    def set_random_unweighted_user(self) -> int:
        """Sets a random user as the current user. Doesn't care about reputation."""
        return self.__set_new_random_user(self.get_unweighted_list())
    
    
    def __set_new_random_user(self, listToChooseFrom:list) -> int:
        """Sets a random user from the list as the current user

        Args:
            listToChooseFrom (list): the list to choose a random user from

        Returns:
            int: the random user now set as the current user
        """
        
        lastUserID = user_manager.get_current_user()

        new_user = secrets.choice(listToChooseFrom)
        
        # Makes sure the same user doesn't go twice in a row
        # Won't check if there's only one user to avoid infinite loops
        if(len(set(listToChooseFrom)) > 1):
            while str(new_user) == lastUserID:
                new_user = secrets.choice(listToChooseFrom)
                print("same user, trying again")
        
        os.remove("user.txt")
        with open('user.txt', 'w') as f:
            f.write(str(new_user))
        
        return new_user



    @staticmethod
    def get_current_user():
        """Returns the current user"""
        file = open("user.txt", "r")
        currentUserID = file.read()
        file.close()
        return currentUserID

    def add_user(self, id):
        """Adds the given user to the list of users"""
        if id not in self.get_weighted_list():
            for i in range(0, config.DEFAULT_REPUTATION):
                self.weighted_list_of_users.append(id)
        self.serialize()

    def remove_user(self, id):
        """Removes the given user from the list of users"""
        for i in range(0, collections.Counter(self.weighted_list_of_users)[id]):
            self.weighted_list_of_users.remove(id)
        self.serialize()

    def boost_user(self, id):
        """Boosts the given user's reputation"""
        if(collections.Counter(self.weighted_list_of_users)[id] < config.MAX_REPUTATION):
            self.weighted_list_of_users.append(id)
        self.serialize()
        print('boosted {0} finished'.format(id))

    def unboost_user(self, id):
        """Reduces the given user's reputation"""
        if(collections.Counter(self.weighted_list_of_users)[id] > 2):
            self.weighted_list_of_users.remove(id)
        self.serialize()
        print('unboosted {0} successful'.format(id))

    def get_weighted_list(self):
        return self.weighted_list_of_users

    def get_unweighted_list(self):
        return set(self.weighted_list_of_users)

    def serialize(self):
        with open('weighted list of users.json', 'w') as f:
            json.dump(self.weighted_list_of_users, f, indent=4)
