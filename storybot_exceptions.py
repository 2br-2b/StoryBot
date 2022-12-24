class TooManyArchivedStoriesException(Exception):
    "Is raised when a user tries to create a new story but already has the maximum number of stories in a given server"
    pass

class ConfigValueNotFoundException(Exception):
    "Is raised when a config value is asked for but isn't found in config.py"
    pass

class NotInGuildException(Exception):
    "Is raised when a config value is asked for but isn't found in config.py"
    pass

class TooMuchProfanityError(Exception):
    "Is raised when a message either has too much profanity to filter out or cannot be added due to the content of the message"
    pass