class TooManyArchivedStoriesException(Exception):
    "Is raised when a user tries to create a new story but already has the maximum number of stories in a given server"
    pass