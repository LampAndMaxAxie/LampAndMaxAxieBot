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

### Guide
1. Adding Managers. This must be done by the ownerDiscordId configured in the config.cfg; there can only be ONE owner. `&addManager discordID`
2. Removing Managers. This must be done by the ownerDiscordId configured in the config.cfg; there can only be ONE owner. `&removeManager discordID`
3. Add Scholars. This can be done by owner/managers. `&addScholar seedNum accountNum discordID scholarShare`. `scholarShare` is between 0.01 to 1.00.
4. Remove Scholars. This can be done by owner/managers. `&removeScholar discordID`
5. Update Scholar Share. This can be done by owner/managers. `&updateScholarShare discordID scholarShare`. `scholarShare` is between 0.01 to 1.00.
6. Set Scholar Payout Address. This can be done by the scholar themself, or by owner/managers. `&setPayoutAddress addr [discordID]`. discordID is optional and only usable by owner/managers.
7. Get Scholars. This can be done by anyone, and simply returns the current information about a scholar. `&getScholar [discordID]`. If discordID is left out it uses the caller.
8. Membership Report. This reports on the member counts for different roles in the user database. `&membership`
9. Mass Payout. This triggers a payout for all scholars in the database, skipping those not ready or without a payout address set. `&massPayout`
10. Indvidual Payout. This can only be triggered by a scholar themselves. `&payout`

If you've run a mass payout, then individual payouts are disabled. This is because running individual payouts during a mass payout could have undesirable effects. If you want to re-enable individual payouts, run `&setProperty massPay 0`.

The options for `&getProperty property`/equivalent setter are `devDonation` and `massPay`.

For other utility commands, run the `&help` command on your active bot.

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

### Transparency / Developer Donations
The bot comes with a default 2.5% (0.025) developer donation configured. You can decrease/increase this with `&setProperty devDonation 0.04`, for 4% as an example. A value of 0 disables it, but please consider supporting us as we've put hundreds of payless hours into this project.

### Scholar Import Script
The script `importScholars.py` depends on: `config.cfg`, `import.txt`, and `SecretStorage.py`. So make sure your `config.cfg` and `import.txt` are filled out before running it. The `SecretStorage.py` really just needs the bot token, since the import script will run as a bot that terminates.

Explanation of `import.txt`:
seedNum: refers to which seedphrase this wallet is on. If you only have one seedphrase, then every row should have a `1` here.
accountNum: refers to which wallet on the seedphrase is used. For example, the top wallet on the ronin extension would be `1`. Make sure you don't count any imported hardware wallets.
discordID: the scholar's discord ID
scholarShare: the scholar share, between 0.01 to 1.00

The bot does not yet use seed phrases, this data entry is just in preparation for when `SecretStorage.py` of private keys becomes obsolete and we switch to encrypted seed phrase mnemonics instead, which we will index by seed phrase and wallet order on that seed phrase.

To run the import, just do `python3 importScholars.py`

