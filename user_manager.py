#import userIDs
import random
import os
import userIDs
import collections
import json

class user_manager():
    def __init__(self):
        self.default_count = 20
        self.maximum_times_in_the_list = 22
        self.listOfUsers = userIDs.userIDs
        
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
                    

    def get_random_user(self):
        file = open("user.txt", "r")
        userID = file.read()
        file.close()
        self.listOfUsers = userIDs.userIDs

        new_user = random.choice(self.listOfUsers)
        while str(new_user) == userID:
            new_user = random.choice(self.listOfUsers)
        
        os.remove("user.txt")
        with open('user.txt', 'w') as f:
            f.write(str(new_user))

        file = open("story.txt", "r")
        userID = file.read()
        file.close()

        return new_user
    
    def get_current_user(self):
        file = open("user.txt", "r")
        userID = file.read()
        file.close()
        print ("`"+userID+"`")
        return userID


    def add_user(self, id):
        if id not in self.get_list():
            for i in range(0, self.default_count):
                self.weighted_list_of_users.append(id)
        self.serialize()

    def remove_user(self, id):
        for i in range(0, collections.Counter(self.weighted_list_of_users)[id]):
            self.weighted_list_of_users.remove(id)
        self.serialize()

    def boost_user(self, id):
        if(collections.Counter(self.weighted_list_of_users)[id] < self.maximum_times_in_the_list):
            self.weighted_list_of_users.append(id)
        self.serialize()
        print('boosted: {0}'.format(id))

    def unboost_user(self, id):
        if(collections.Counter(self.weighted_list_of_users)[id] > 1):
            self.weighted_list_of_users.remove(id)
        self.serialize()
        print('unboosted: {0}'.format(id))


    def get_random_weighted_user(self):
        userID = self.get_current_user()
        
        new_user = random.choice(self.weighted_list_of_users)
        while str(new_user) == userID:
            new_user = random.choice(self.weighted_list_of_users)
        
        os.remove("user.txt")
        with open('user.txt', 'w') as f:
            f.write(str(new_user))

        file = open("story.txt", "r")
        userID = file.read()
        file.close()

        return new_user
    

    def get_list(self):
        return self.weighted_list_of_users


    def serialize(self):
        with open('weighted list of users.json', 'w') as f:
            json.dump(self.weighted_list_of_users, f, indent=4)