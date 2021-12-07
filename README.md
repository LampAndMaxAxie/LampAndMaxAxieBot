# Author: Michael Conard

### Code Setup
1. If on Linux, you're good to go. If on Windows, I recommend setting up Windows Subsystem for Linux: https://www.notion.so/Script-Install-Guide-1bfef048044d47dc8c665bbe502a159a
2. Install python3 via your preferred method, if you don't already have it.
3. Setup your github ssh keys: https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent
3. Clone the github repository: `git clone git@github.com:maconard/Lamp-sAxieBot-Base.git`
4. Move the install script from the scripts folder to main folder. `cp scripts/install-ubuntu.sh install.sh` 
5. Run the installation script `./install.sh` to install a lot of the basic libraries used. If running the bot fails, just see what library is missing via the error message and install it with pip3 like `pip3 install <missingLibName>`. Can then remove the script `rm install.sh`.
6. Fill out/replace the values in `config.cfg`. Everything is required.
7. Run `python3 EncryptSeeds.py`. Read the information printed, choose your encryption password, and input your seeds in the order you reference them for your scholars.
8. Go to the Discord Dev Portal site and create a DiscordBot. Can follow a simple tutorial like this one: https://www.freecodecamp.org/news/create-a-discord-bot-with-python/
9. Add the bot's "client token" to the bottom of the `SeedStorage.py` file.

### Bot Setup
When doing O-Auth to add your bot to your Discord server, make sure to grant/do the following:
1. Scopes: bot, applications.commands
2. Permissions: view channels, send messages, embed links, attach files, read message history, add reactions, use slash commands, etc. The bot does NOT need admin privileges.
3. Go to the Bot menu in the Dev Portal and under "Privileged Gateway Intents" enable the "Server Members Intent"

For launching your bot on your server, start with database creation and scholar import/migration. Migration is for if you've been using a previous version of the bot and the new version has database changes.

If migrating (i.e. upgrading to new bot version that needs migration):
1. Make sure your config.cfg file is up to date and accurate.
2. Create your migration file. See the `sampleTexts/` directory for an example for the migration you need.
3. Copy the migration.py file from the scripts folder to the main code file.
3. From your main bot directory, run `migration1.py myMigrationFile.txt` for whichever migration script and input text you need.

If importing (i.e. first time using the bot):
1. Make sure your config.cfg file is up to date and accurate.
2. Create your import file. Currently this takes the form: `seedNum, accountNum, accountAddr, discordId, scholarShare`, see `sampleTexts/` for an example.
3. Copy the importScholars.py file from the scripts folder to the main code file.
3. From your main bot directory, run `importScholars.py myImportFile.txt` for your input file. 
Note, importing like this is only necessary if you have a large number of scholars and don't want to add them to the bot one by one via Guide item 3 below. Can delete the script and import file when no longer needed.

### Guide
1. Adding Managers. This must be done by the ownerDiscordId configured in the config.cfg; there can only be ONE owner. `&addManager discordID`
2. Removing Managers. This must be done by the ownerDiscordId configured in the config.cfg; there can only be ONE owner. `&removeManager discordID`
3. Add Scholars. This can be done by owner/managers. `&addScholar seedNum accountNum roninAddr discordID scholarShare payoutAddr`. `scholarShare` is between 0.50 to 1.00. `payoutAddr` is optional, if you happen to have it; scholars can set it themselves via the bot.
4. Remove Scholars. This can be done by owner/managers. `&removeScholar discordID`
5. Update Scholar Share. This can be done by owner/managers. `&updateScholarShare discordID scholarShare`. `scholarShare` is between 0.01 to 1.00.
6. Set Scholar Payout Address. This can be done by the scholar themself, or by owner/managers. `&setPayoutAddress addr [discordID]`. discordID is optional and only usable by owner/managers.
7. Get Scholars. This can be done by anyone, and simply returns the current information about a scholar. `&getScholar [discordID]`. If discordID is left out it uses the caller.
8. Membership Report. This reports on the member counts for different roles in the user database. `&membership`
9. Mass Payout. This triggers a payout for all scholars in the database, skipping those not ready or without a payout address set. `&massPayout`
10. Indvidual Payout. This can only be triggered by a scholar themselves. `&payout`

If you've run a mass payout, then individual payouts are disabled. This is because running individual payouts during a mass payout could have undesirable effects. If you want to re-enable individual payouts, run `&setProperty massPay 0`.

For other utility commands, run the `&help` command on your active bot.

### Main Features List
1. DM QR codes to scholars on request
2. Automatically claim SLP and payout to scholars, either triggered in bulk or scholars can individually request.
3. Fetch the Axie teams from a scholars account, displays their level and parts/stats
4. Get scholar daily progress regarding Adventure SLP and Daily Quest completion
5. Generate a scholar summary of all scholars, ranked on what you'd like to sort by
6. Automatically sends alerts in a specified channel an hour before reset if people are missing progress
7. Automatically post summaries in a specified channel at some interval of hours. Set the leaderboardPeriod to 25 to disable.
8. Get recent battles for a scholar/ronin address (disabled by Axie servers)

### Additional Information
NOTE: slash commands currently not functioning.

Supports text commands with prefix and slash commands! Note that embeds in slash commands can't contain images due to "API limitations" (quote the shitty API docs), so if you want the images in `battles` and `axies` calls, use a text command instead of a slash command.

Feel free to reach out to MaikeruKonare#3141 on Discord for support or bug reports.

I'd recommend you run the bot using a supervisor service, such as `supervisord`, so that it runs on machine boot up and re-launches itself on crashes. You can configure stdout and stderr logging to land where you'd like. Otherwise, you could run the bot in a `tmux` or `screen` instance; this would be manual start up but then it would keep running. Up to you. If you're not using your own machine, you can use a secure Amazon EC2 instance.

The bot will create a folder called `qr` where it will cache QR images for sending to scholars when they request them. You can regularly empty this folder if you'd like, it doesn't matter. New QR codes will overwrite old ones.

The bot will create a file `jftTokens.json` which contains the Axie Infinity game-api authentication/bearer token. This will cache for many days to reduce requests for new tokens. The Ronin private keys in `SecretStorage.py` are used to compute this file and nothing else. In the future, the ability to configure scholar payouts will be implemented.

Daily data requested and used by the bot is only cached in-memory and won't be saved over machine reboot or application re-launch.

If you create a custom icon called exactly `:slp:` (yes, lowercase) then the bot will use that emoji as needed.

### Transparency / Developer Donations
The bot comes with a default 1% (0.01) developer donation configured. We've put hundreds of payless hours into this project, and every SLP helps. If this is a problem, or if you'd like to donate a higher percentage, please reach out to us.

