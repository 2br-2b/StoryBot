class TooManyArchivedStoriesException(Exception):
    "Is raised when a user tries to create a new story but already has the maximum number of stories in a given server"
    pass

class ConfigValueNotFoundException(Exception):
    "Is raised when a config value is asked for but isn't found in config.py"
    pass

class NotInGuildException(Exception):
    "Is raised when a config value is asked for but isn't found in config.py"
    pass