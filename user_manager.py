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
        
        
        
        self.listOfUsers = config.defaultUserIDs
        
        # Create the initial list of users
        try:
            with open('weighted list of users.json', 'rt') as f:
                self.weighted_list_of_users = json.load(f)
            for id in self.weighted_list_of_users:
                if(collections.Counter(self.weighted_list_of_users)[id] > self.maximum_times_in_the_list):
                    self.unboost_user(id)
        except:
            self.weighted_list_of_users = []
            for item in self.listOfUsers:
                self.add_user(item)
                    

    # Chooses a random user
    # Doesn't care about reputation
    def get_random_user(self):
        userID = user_manager.get_current_user()

        new_user = random.choice(self.listOfUsers)
        while str(new_user) == userID:
            new_user = random.choice(self.listOfUsers)
        
        os.remove("user.txt")
        with open('user.txt', 'w') as f:
            f.write(str(new_user))

        return new_user
    
    # Returns the current user
    @staticmethod
    def get_current_user():
        file = open("user.txt", "r")
        userID = file.read()
        file.close()
        print ("Current user retrieved: `"+userID+"`")
        return userID

    # Adds the given user to the list of users
    def add_user(self, id):
        if id not in self.get_list():
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

    # Gets a random user from the list based on their reputation
    def get_random_weighted_user(self):
        userID = user_manager.get_current_user()
        
        new_user = random.choice(self.weighted_list_of_users)
        while str(new_user) == userID:
            new_user = random.choice(self.weighted_list_of_users)
        
        os.remove("user.txt")
        with open('user.txt', 'w') as f:
            f.write(str(new_user))

        return new_user
    

    def get_list(self):
        return self.weighted_list_of_users


    def serialize(self):
        with open('weighted list of users.json', 'w') as f:
            json.dump(self.weighted_list_of_users, f, indent=4)
