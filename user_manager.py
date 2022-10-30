#import userIDs
import random
import os
import config
import collections
import json

class user_manager():
    def __init__(self, bot):
        self.bot = bot
        
        self.default_count = config.DEFAULT_REPUTATION
        self.maximum_times_in_the_list = config.MAX_REPUTATION
        
        self.defaultListOfUsers = config.defaultUserIDs
        
        # Create the initial list of users
        try:
            with open('weighted list of users.json', 'rt') as f:
                self.weighted_list_of_users = json.load(f)
            for id in self.weighted_list_of_users:
                if(collections.Counter(self.weighted_list_of_users)[id] > self.maximum_times_in_the_list):
                    self.unboost_user(id)
        except:
            self.weighted_list_of_users = []
            for item in self.defaultListOfUsers:
                self.add_user(item)
      
      
    
    # Gets a random user from the list based on their reputation
    def set_random_weighted_user(self) -> int:
        return self.__set_new_random_user(self.get_weighted_list())
    
    # Chooses a random user
    # Doesn't care about reputation
    def set_random_unweighted_user(self) -> int:
        return self.__set_new_random_user(self.get_unweighted_list())
    
    
    def __set_new_random_user(self, listToChooseFrom) -> int:
        lastUserID = user_manager.get_current_user()

        new_user = random.choice(listToChooseFrom)
        
        # Makes sure the same user doesn't go twice in a row
        # Won't check if there's only one user to avoid infinite loops
        if(len(set(listToChooseFrom)) > 1):
            while str(new_user) == lastUserID:
                new_user = random.choice(listToChooseFrom)
                print("same user, trying again")
        
        os.remove("user.txt")
        with open('user.txt', 'w') as f:
            f.write(str(new_user))
        
        return new_user
    
    
    
    
    # Returns the current user
    @staticmethod
    def get_current_user():
        file = open("user.txt", "r")
        currentUserID = file.read()
        file.close()
        return currentUserID

    # Adds the given user to the list of users
    def add_user(self, id):
        if id not in self.get_weighted_list():
            for i in range(0, self.default_count):
                self.weighted_list_of_users.append(id)
        self.serialize()

    # Removes the given user from the list of users
    def remove_user(self, id):
        for i in range(0, collections.Counter(self.weighted_list_of_users)[id]):
            self.weighted_list_of_users.remove(id)
        self.serialize()

    # Boosts the given user's reputation
    def boost_user(self, id):
        if(collections.Counter(self.weighted_list_of_users)[id] < self.maximum_times_in_the_list):
            self.weighted_list_of_users.append(id)
        self.serialize()
        print('boosted {0} finished'.format(id))

    # Reduces the given user's reputation
    def unboost_user(self, id):
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
