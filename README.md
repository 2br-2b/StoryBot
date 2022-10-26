# StoryBot


## Setting up the bot
1. Clone or [download](https://github.com/2br-2b/StoryBot/archive/refs/heads/master.zip) the repository
2. Navigate into the directory
3. Run `pip3 install -r requirements.txt`
4. Copy `config.py.default` to `config.py` and modify the values as needed
5. Run `python3 main.py` to start the bot running!

## Reputation
Each user writing the story has a reputation. Reputation is kept so that if someone times out often, they'll end up being chosen less often so that they're less likely to keep other players waiting.

Reputation is a value from 1 to 22 representing how many times the user is in the weighted_list_of_users. The default reputation for a new user is 20.

After the story is added to, a new user is chosen based off of a weighted random number using each user's reputation.

### Gaining and losing reputation
Reputation can be gained in the following ways:
- Adding to the story gains one reputation
- An admin command can add reputation to a user

Reputation can be lost in the following ways:
- Timing out (skipping your turn does not cause a loss of reputation)
- An admin command can remove reputation from a user

## Some of my design considerations (from like three years ago)
- I kept everything in plaintext so that it'd be easy for me to go through and edit whatever values I needed to on the fly. In addition, I usually have the bot check values in the file system so that if I change the current user, I don't have to restart the bot.
- Some hardcoded values need to be removed
- [dmlistener.py](dmlistener.py) is in charge of interfacing the bot with Discord and is responsible for most of the logic that goes on
- [file_manager.py](file_manager.py) is in charge of saving and modifying the story
- [user_manager.py](user_manager.py) is in charge of keeping track of who's playing and choosing random users based on reputation
