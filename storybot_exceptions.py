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

class UserNotFoundFromStringError(Exception):
    "Is raised when a user is not found when converting a string to a user"
    pass

class UserIsBannedException(Exception):
    "Is raised when a user tries to join a story but is banned"
    pass

class NoValidUndoCommand(Exception):
    "Is raised when a user tries to `/undo` the last story chunk but either there isn't a story file or the last log doesn't have a character length"
    pass

class NotAnAuthorException(Exception):
    "Is raised when an action would need to involve a user being an author in a guild, but this isn't the case"
    pass