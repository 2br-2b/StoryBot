# StoryBot

## Notice: bot under active development

I just resumed work on this after a few years, and I'm working on making it better in many ways. The latest release works fine, and cloning from the repo at any given time should still work, but lots of major changes are still happening on the backend!

Expect changes in the individual methods, the file structure, configuration, etc. I first wrote this code 3 years ago during my freshman year at college, so some parts of the program are not written as well as they should have been. I am thus in the process of making revisions to large portions of the codebase.

## What this bot is

This Discord bot is called StoryBot. After it is given a list of users, it will choose one at random to begin writing a story. After this person makes their addition to the story, another user will be chosen at random to continue the story. This will continue on until the story is completed. Since each subsequent author is chosen at random, there is no way to prepare for whatever cameos or inside jokes the next author may enter. Fair warning: the story will be chaos.

In order to make sure the story progresses regularly, the bot implements a timeout system. After you are chosen as the active user, you have a set period of time (24 hours by default, but this can be changed by the server admin) to add onto the story. If you do not write within this given amount of time, your turn is automatically skipped. You also lose a [reputation point](#reputation), making you slightly less likely to chosen again in the future. This reputation can be regained by actively contributing to the story on future turns.

## Setting up the bot
1. Set up a Postgres database and store the credentials/port
2. Clone the repository (unstable) or [download the latest release (stable)](https://github.com/2br-2b/StoryBot/releases)
3. Navigate into the directory
4. Run `pip3 install -r requirements.txt`
5. Copy `config.py.default` to `config.py` and modify the values as needed
6. Run `python3 main.py` to start the bot running!

If you have any problems while setting up the bot, feel free to [start a discussion](https://github.com/2br-2b/StoryBot/discussions) or [open an issue](https://github.com/2br-2b/StoryBot/issues).

## Reputation
Each user writing the story has a reputation. Reputation is kept so that if someone times out often, they'll end up being chosen less often so that they're less likely to keep other players waiting.

Reputation is a value from 1 to 20 representing a number of "tickets" in a weighted random lottery. Whichever user is chosen in this lottery will go next.

The default reputation for a new user is 20, the maximum; bear in mind, however, that individual servers can customize these values.

After the story is added to, a new user is chosen based off of a weighted random number using each user's reputation.

### Gaining and losing reputation
Reputation can be gained in the following ways:
- Adding to the story gains one reputation
- An admin can manually increase a user's reputation
- If you pause yourself for a day or more, when you automatically unpause, you'll gain a reputation point

Reputation can be lost in the following ways:
- Timing out loses one reputation point (manually skipping your turn does not cause a loss of reputation)
- An admin can manually decrease a user's reputation

## Safe Mode

For those who need moderation, I'm working on it - look [here](https://github.com/2br-2b/StoryBot/issues?q=is%3Aissue+label%3Amoderation) to see the progress. I've started with adding "Safe Mode" to the bot. Safe Mode is __disabled by default__ and will do its best to filter out vulgar words and replace them with \*s. Safe Mode will likely do more in the future (check for links, etc), but it does not do anything of this sort yet. It is nowhere near perfect and can be circumvented rather easily, but I wanted to implement this optional feature as well as the Safe Mode toggle to start adding optional moderation features.

Even if safe mode is activated, all language checking will be done locally (so your stories will not be sent off or processed by a third party). The current implementation is done thru the (better-profanity python library) [https://github.com/snguyenthanh/better_profanity], and even that lists some examples of how to circumvent it. My goal is not to prevent anyone from using profanity in their stories, but rather to give server operators the option to make it more inconvenient for trolls to use vulgarity.

Moderation is still in a very early stage, so I always appreciate feedback on how its implemented, ideas on how it could be made better, and the like.

To enable profanity filters, run `/configure setting:SafeModeEnabled value:true`

## Program Structure
- [dm_listener.py](cogs/dm_listener.py) is in charge of interfacing the bot with Discord and is responsible for most of the logic that goes on
- [file_manager.py](file_manager.py) is in charge of saving and modifying the story
- [user_manager.py](user_manager.py) is in charge of keeping track of who's playing and choosing random users based on reputation
- [config.py](config.py.default) lists the server admin's preferences for the bot's behavior

## License notice

As of right now, this program does not have a license. This will change in the future. The goal is to have a non-commercial license so that people can learn from this without being able to swoop in and make money off of a project I've put my unpaid free time into.

I intend to maintain all rights to the source code produced for this project but to grant a non-commercial license to anyone who wants one; however, this license is still to be determined and the repository **does not** yet have a license allowing you to use or copy this source code. This section is merely a heads up to let you know a bit about the future of this project and is not a license to use this source code.
