# Author: Michael Conard

### Code Setup
1. Install python3 via your preferred method, if you don't already have it.
2. Run the installation script to install a lot of the basic libraries used. If running the bot fails, just see what library is missing via the error message and install it with pip3 like `pip3 install <missingLibName>`.
3. Fill out/replace the values in `config.cfg`. Everything is required.
4. Fill out the `SecretStorage.py` file with scholar Discord ID/name and your Ronin address/key; this is to match wallets to scholars and to gain access to authenticated/private game-api data such as QR/daily progress/earnings. Make sure to put them in the right order. This is still required, but won't be one mnemonic processing is implemented.
5. Go to the Discord Dev Portal site and create a DiscordBot. Can follow a simple tutorial like this one: https://www.freecodecamp.org/news/create-a-discord-bot-with-python/
6. Add the bot's "client secret" to the `SecretStorage.py` file.

### Bot Setup
When doing O-Auth to add your bot to your Discord server, make sure to grant/do the following:
1. Scopes: bot, applications.commands
2. Permissions: view channels, send messages, embed links, attach files, read message history, add reactions, use slash commands, etc.
3. Go to the Bot menu in the Dev Portal and under "Privileged Gateway Intents" enable the "Server Members Intent"

### Main Features List
1. DM QR codes to scholars on request
2. Automatically claim SLP and payout to scholars, either triggered in bulk or scholars can individually request.
3. Fetch the Axie teams from a scholars account, displays their level and parts/stats
4. Get scholar daily progress regarding Adventure SLP and Daily Quest completion
5. Generate a scholar summary of all scholars, ranked on what you'd like to sort by
6. Automatically sends alerts in a specified channel an hour before reset if people are missing progress
7. Automatically post summaries in a specified channel at some interval of hours. Set the leaderboardPeriod to 25 to disable.
8. Get recent battles for a scholar/ronin address

### Additional Information
Supports text commands with prefix and slash commands! Note that embeds in slash commands can't contain images due to "API limitations" (quote the shitty API docs), so if you want the images in `battles` and `axies` calls, use a text command instead of a slash command.

Feel free to reach out to MaikeruKonare#3141 on Discord for support or bug reports.

I'd recommend you run the bot using a supervisor service, such as `supervisord`, so that it runs on machine boot up and re-launches itself on crashes. You can configure stdout and stderr logging to land where you'd like. Otherwise, you could run the bot in a `tmux` or `screen` instance; this would be manual start up but then it would keep running. Up to you. If you're not using your own machine, you can use a secure Amazon EC2 instance.

The bot will create a folder called `qr` where it will cache QR images for sending to scholars when they request them. You can regularly empty this folder if you'd like, it doesn't matter. New QR codes will overwrite old ones.

The bot will create a file `jftTokens.json` which contains the Axie Infinity game-api authentication/bearer token. This will cache for many days to reduce requests for new tokens. The Ronin private keys in `SecretStorage.py` are used to compute this file and nothing else. In the future, the ability to configure scholar payouts will be implemented.

Daily data requested and used by the bot is only cached in-memory and won't be saved over machine reboot or application re-launch.

If you create a custom icon called exactly `:slp:` (yes, lowercase) then the bot will use that emoji as needed.

