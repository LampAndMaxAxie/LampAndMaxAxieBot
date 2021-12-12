# Author: Michael Conard
# Purpose: An Axie Infinity utility bot. Gives QR codes and daily progress/alerts.
import asyncio
import datetime
import os
import time

import discord
import pandas as pd
import plotly.graph_objects as go
from loguru import logger
from web3 import Web3

import ClaimSLP
import Common
import DB
import UtilBot
from Common import prefix, dmPayoutsToScholars


# Returns information on available commands
async def helpCommand(message, isManager, discordId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()

    msg = 'Hello <@' + str(discordId) + '>! Here are the text command options:\n'
    msg += ' - `' + prefix + 'help`: returns this help message\n'
    msg += ' - `' + prefix + 'daily [name/ping/discordID]`: returns the player\'s match/SLP/quest data for today\n'
    msg += ' - `' + prefix + 'axies [name/ping/discordID] [index] [m]`: returns the player\'s Axies, [index] is to select a team (default 0), set [m] for mobile friendly\n'
    #msg += ' - `' + prefix + 'battles [name/ping/discordID]`: returns the scholar\'s recent battle records\n'
    msg += ' - `' + prefix + 'summary [sort] [ascending] [csv]`: returns a scholar summary, [avgslp/slp, mmr/rank, claim], [asc, desc], [csv]\n'
    msg += ' - `' + prefix + 'top [sort] [csv]`: returns the scholar top 10 rankings, [avgslp/slp, mmr/rank, claim], [csv]\n'
    msg += ' - `' + prefix + 'membership`: returns information about the status of the user database\n'

    if not isManager: # scholar
        msg += ' - `' + prefix + 'qr`: DMs you your QR code to login to the mobile app\n'
        msg += ' - `' + prefix + 'login`: DMs you your login info if your manager set it up\n'
        msg += ' - `' + prefix + 'setPayoutAddress roninAddress`: sets the user\'s payout address, can be ronin: or 0x form\n'
        msg += ' - `' + prefix + 'payout discordID`: triggers a payout for the user\n'

    else: # manager
        msg += ' - `' + prefix + 'export`: returns a listing of scholar information from the database\n'
        msg += ' - `' + prefix + 'exportRole role`: returns a spreadsheet of users with a role; finds the closest match ("Scho" would likely find "Scholar")\n'
        msg += ' - `' + prefix + 'getScholar [discordID]`: returns information on the caller, or the specified discord ID\n'
        msg += ' - `' + prefix + 'addScholar seedNum accountNum accountAddr discordID scholarShare [scholarPayoutAddr]`: add a scholar to the database; scholar share is 0.50 to 1.00\n'
        msg += ' - `' + prefix + 'removeScholar discordID`: removes the user\'s status as a scholar\n'
        msg += ' - `' + prefix + 'addManager discordID`: add a manager to the database\n'
        msg += ' - `' + prefix + 'removeManager discordID`: removes the user\'s status as a manager\n'
        msg += ' - `' + prefix + 'updateScholarShare discordID scholarShare`: sets the user\'s share to the new value, 0.50 to 1.00\n'
        msg += ' - `' + prefix + 'setPayoutAddress roninAddress discordID`: sets the specified user\'s payout address, can be ronin: or 0x form\n'
        msg += ' - `' + prefix + 'setAccountLogin discordID roninAddress email pass`: records the account\'s login info, only usable by managers\n'
        msg += ' - `' + prefix + 'setProperty property value`: sets a property to a value (like "massPay 0" to enable individual payouts)\n'
        msg += ' - `' + prefix + 'getProperty property`: gets a property\'s value (try "massPay")\n'
        msg += ' - `' + prefix + 'massPayout [seedFilter] [minIndex] [maxIndex]`: triggers a scholar payout for all scholars, optional filters\n'
        msg += ' - `' + prefix + 'payout discordID`: triggers a payout for the specified user\n'

    await Common.handleResponse(message, msg, isSlash)
    return


# DM the caller their QR login code
async def qrCommand(message, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()

    if os.path.exists("./qr/" + str(message.author.id) + "QRCode.png"):
        os.remove("./qr/" + str(message.author.id) + "QRCode.png")

    current_time = datetime.datetime.now().strftime("%H:%M:%S")

    # check for user's Discord ID
    if message.author.id in Common.qrBlacklist:
        msg = "Sorry, but QR generation isn't working for your account right now. Please talk to your manager."
        await message.author.send(msg)

        if guildId is not None:
            msg = 'Hi <@' + str(discordId) + '>, please check your DMs!'
            await Common.handleResponse(message, msg, isSlash)

        return

    author = await DB.getDiscordID(message.author.id)
    if author["success"] and author["rows"]["is_scholar"]:
        logger.info("This user received their QR Code : " + message.author.name)

        scholar = author["rows"]

        accountPrivateKey, accountAddress = await UtilBot.getKeyForUser(scholar)
        if accountPrivateKey is None or accountAddress is None:
            await Common.handleResponse(message, "Mismatch detected between configured scholar account address and seed/account indices, or scholar not found.", isSlash)
            return

        logger.info(f"Scholar {discordId} account addr confirmed as {accountAddress} via mnemonic")

        if accountPrivateKey == "" or accountAddress == "":
            msg = 'Sorry <@' + str(discordId) + '>, your manager has not configured QR code generation.'
            await Common.handleResponse(message, msg, isSlash)
            return

        accessToken = UtilBot.getPlayerToken(accountPrivateKey, accountAddress)

        if accessToken is None:
            msg = 'Sorry <@' + str(discordId) + '>, there was an issue with your request. Please try again later.'
            await Common.handleResponse(message, msg, isSlash)
            return

        # Create a QrCode with that accessToken
        qrFileName = UtilBot.getQRCode(accessToken, message.author.id)

        # Send the QrCode the the user who asked for
        if isSlash:
            # respond with hidden message QR
            await message.edit(content="QR code sent!")
            await message.channel.send(content="Here is your new QR Code to login, remember to always keep it safe and not to let anyone else see it:", file=discord.File(qrFileName), flags=(1<<6))

            #msg = 'Hi <@' + str(discordId) + f">, this slash command isn\'t implemented yet! Please try {prefix}qr"
            #await Common.handleResponse(message, msg, isSlash)

        else:
            # respond with DM
            await message.author.send(
                "------------------------------------------------\n\n\nHello " + message.author.name + "\nHere is your new QR Code to login: ")
            await message.author.send(file=discord.File(qrFileName))
            await message.author.send("Remember to keep your QR code safe and don't let anyone else see it!")

            if guildId is not None:
                msg = 'Hi <@' + str(discordId) + '>, please check your DMs!'
                await Common.handleResponse(message, msg, isSlash)

        return

    else:
        logger.warning("This user didn't receive a QR Code : " + message.author.name)
        msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + Common.programName + '\'s scholars.'

        await Common.handleResponse(message, msg, isSlash)
        return


# DM the caller their login info
async def loginInfoCommand(message, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()
    
    current_time = datetime.datetime.now().strftime("%H:%M:%S")

    # check for user's Discord ID
    if message.author.id in Common.qrBlacklist:
        msg = "Sorry, but login isn't working for your account right now. Please talk to your manager."
        await message.author.send(msg)

        if guildId is not None:
            msg = 'Hi <@' + str(discordId) + '>, please check your DMs!'
            await Common.handleResponse(message, msg, isSlash)

        return

    author = await DB.getDiscordID(message.author.id)
    if author["success"] and author["rows"]["is_scholar"]:
        logger.info("This user received their login info : " + message.author.name)

        scholar = author["rows"]

        email = scholar["account_email"]
        password = scholar["account_pass"]

        if email is None or password is None:
            msg = 'Sorry <@' + str(discordId) + '>, your manager has not configured login info.'
            await Common.handleResponse(message, msg, isSlash)
            return

        # Send the info to the user who asked for it
        if isSlash:
            # respond with hidden message with info
            await message.edit(content=f"Here is your login info, remember to always keep it safe and not to let anyone else see it:\nEmail: ||{email}||\nPassword: ||{password}||", flags=(1<<6))

            #msg = 'Hi <@' + str(discordId) + f">, this slash command isn\'t implemented yet! Please try {prefix}login"
            #await Common.handleResponse(message, msg, isSlash)

        else:
            # respond with DM
            await message.author.send(
                "------------------------------------------------\n\n\nHello " + message.author.name + "\nHere is your new info to login: ")
            await message.author.send(f"Email: ||{email}||\nPassword: ||{password}||")
            await message.author.send(f"Remember to keep your login info safe and don't let anyone else see it!")

            if guildId is not None:
                msg = 'Hi <@' + str(discordId) + '>, please check your DMs!'
                await Common.handleResponse(message, msg, isSlash)

        return

    else:
        logger.warning("This user didn't receive login info : " + message.author.name)
        msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + Common.programName + '\'s scholars.'

        await Common.handleResponse(message, msg, isSlash)
        return


# Set a database property, such as massPay
async def setPropertyCommand(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isManager(authorID):
        await Common.handleResponse(message, "You must be a manager to use this command", isSlash)
        return

    if len(args) < 3:
        await Common.handleResponse(message, f"Please enter: {prefix}setProperty property value", isSlash)
        return

    prop = args[1]
    val = args[2]

    res = await DB.setProperty(prop, val)
    await Common.handleResponse(message, res["msg"], isSlash)


# Get a database property, such as massPay
async def getPropertyCommand(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id

    if len(args) < 2:
        await Common.handleResponse(message, f"Please enter: {prefix}getProperty property", isSlash)
        return

    prop = args[1]

    res = await DB.getProperty(prop)

    if not res["success"] or (res["success"] and res["rows"] is None):
        await Common.handleResponse(message, f"Failed to get property {prop}", isSlash)
        return

    realV = res["rows"]["realVal"]
    textV = res["rows"]["textVal"]

    val = realV
    if realV is None:
        val = textV

    embed = discord.Embed(title="Property Information", description=f"Request for property {prop}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name="Property", value=f"{prop}")
    embed.add_field(name="Value", value=f"{val}")

    if isSlash:
        await message.edit(embed=embed)
    else:
        await message.reply(embed=embed)


# Command helper to issue and check a confirmation embed to the caller
async def processConfirmationAuthor(message, embed, timeoutSecs=None):
    authorID = message.author.id
    confMsg = await message.channel.send(embed=embed)

    greenCheck = "\N{White Heavy Check Mark}"
    redX = "\N{Cross Mark}"
    options = [greenCheck, redX]

    await confMsg.add_reaction(greenCheck)
    await confMsg.add_reaction(redX)

    def check(reaction, user):
        emoji = UtilBot.getEmojiFromReact(reaction)
        return int(user.id) == int(authorID) and emoji in options and int(reaction.message.id) == int(confMsg.id)

    try:
        reaction, user = await Common.client.wait_for('reaction_add', timeout=timeoutSecs, check=check)
        emoji = UtilBot.getEmojiFromReact(reaction)
        if emoji == greenCheck:
            return confMsg, True
        elif emoji == redX:
            return confMsg, False
        else:
            return confMsg, None

    except asyncio.TimeoutError:
        return confMsg, None


# Command helper to issue and check a confirmation embed for any manager
async def processConfirmationManager(message, embed, timeoutSecs=None):
    authorID = message.author.id
    mgrIds = await DB.getAllManagerIDs()

    confMsg = await message.channel.send(embed=embed)

    greenCheck = "\N{White Heavy Check Mark}"
    redX = "\N{Cross Mark}"
    options = [greenCheck, redX]

    await confMsg.add_reaction(greenCheck)
    await confMsg.add_reaction(redX)

    def check(reaction, user):
        emoji = UtilBot.getEmojiFromReact(reaction)
        return user.id in mgrIds and emoji in options and reaction.message == confMsg

    try:
        reaction, user = await Common.client.wait_for('reaction_add', timeout=timeoutSecs, check=check)
        emoji = UtilBot.getEmojiFromReact(reaction)
        if emoji == greenCheck:
            return confMsg, True
        elif emoji == redX:
            return confMsg, False
        else:
            return confMsg, None

    except asyncio.TimeoutError:
        return confMsg, None


# Get a scholar's data
async def getScholar(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id

    if len(args) > 1 and not args[1].isnumeric():
        await Common.handleResponse(message, "Please ensure the discord ID is correct", isSlash)
        return
    if len(args) > 1:
        discordId = int(args[1])

    name = await Common.getNameFromDiscordID(discordId)
    if name is None:
        await Common.handleResponse(message, "Could not find user with that discord ID", isSlash)
        return

    scholarRes = await DB.getDiscordID(discordId)
    if not scholarRes["success"]:
        await Common.handleResponse(message, "Failed to get scholar from database", isSlash)
        return
    if scholarRes["rows"]["is_scholar"] is None or scholarRes["rows"]["is_scholar"] == 0:
        await Common.handleResponse(message, f"Did not find a scholar with discord ID {discordId}", isSlash)
        return

    scholar = scholarRes["rows"]
    scholarShare = round(float(scholar["share"]), 3)
    scholarAddr = scholar["payout_addr"]
    seedNum = scholar["seed_num"]
    accountNum = scholar["account_num"]
    createdTime = scholar["created_at"]
    scholarDate = datetime.datetime.fromtimestamp(int(createdTime)).strftime('%Y-%m-%d %H:%M:%S')

    if Common.hideScholarRonins:
        roninAddr = "<hidden>"
    else:
        roninAddr = scholar["scholar_addr"]

    embed = discord.Embed(title="Scholar Information", description=f"Information about scholar {name}/{discordId}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Scholar Name", value=f"{name}")
    embed.add_field(name=":id: Scholar Discord ID", value=f"{discordId}")
    embed.add_field(name=":bar_chart: Scholar Share", value=f"{round(scholarShare * 100, 2)}%")
    embed.add_field(name=":clock1: Scholar Created", value=f"<t:{createdTime}:D>")
    embed.add_field(name="Seed", value=f"{seedNum}")
    embed.add_field(name="Account", value=f"{accountNum}")
    embed.add_field(name="Account Address", value=f"{roninAddr}")
    embed.add_field(name="Payout Address", value=f"{scholarAddr}")

    if isSlash:
        await message.edit(content=f"<@{authorID}>", embed=embed)
    else:
        await message.reply(content=f"<@{authorID}>", embed=embed)


# Add a scholar to the system
async def addScholar(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isManager(authorID):
        await Common.handleResponse(message, "You must be a manager to use this command", isSlash)
        return

    if len(args) < 5:
        await Common.handleResponse(message, "Please specify: seedNum accountNum roninAddr discordUID scholarShare [payoutAddress]", isSlash)
        return

    seedNum = args[1]
    accountNum = args[2]
    roninAddr = args[3]
    discordUID = args[4]
    payoutAddress = ""
    scholarShare = 0.5  # pull from default config

    if (not seedNum.isnumeric() or int(seedNum) < 1) or (not accountNum.isnumeric() or int(accountNum) < 1) or not str(discordUID).isnumeric():
        await Common.handleResponse(message, "Please ensure your seed/account indices are >= 1 and the discord ID is correct", isSlash)
        return

    if (not roninAddr.startswith("0x")) and (not roninAddr.startswith("ronin:")):
        await Common.handleResponse(message, "Please ensure your ronin address begins with '0x' or 'ronin:'", isSlash)
        return

    roninAddr = roninAddr.replace("ronin:", "0x").strip()

    name = await Common.getNameFromDiscordID(discordUID)
    if name is None:
        await Common.handleResponse(message, "Could not find user with that discord ID", isSlash)
        return

    if len(args) >= 6 and Common.isFloat(args[5]):
        scholarShare = round(float(args[5]), 3)

    if scholarShare < 0.50 or scholarShare > 1.0:
        await Common.handleResponse(message, "Please ensure your scholar share is between 0.50 and 1.00", isSlash)
        return

    if len(args) >= 7 and args[6]:
        payoutAddress = args[6].replace("ronin:","0x").strip()
        if not Web3.isAddress(payoutAddress):
            await Common.handleResponse(message, "Payout address does not appear to be a valid address. Please check it.", isSlash)
            return

    scholarsDB = await DB.getAllScholars()
    if not scholarsDB["success"]:
        await Common.handleResponse(message, "Failed to query database for scholars", isSlash)
        return

    for scholar in scholarsDB["rows"]:
        seedNum2 = int(scholar["seed_num"])
        accNum2 = int(scholar["account_num"])

        if int(seedNum) == seedNum2 and accNum2 == int(accountNum):
            await Common.handleResponse(message, "A scholar already exists with that seed/account pair", isSlash)
            return

    user = {"seed_num": seedNum, "account_num": accountNum, "scholar_addr": roninAddr}
    key, address = await UtilBot.getKeyForUser(user)
    if key is None or address is None:
        await Common.handleResponse(message, "Mismatch detected between given wallet address and seed/account indices, or scholar not found. Please try again with the correct wallet information.", isSlash)
        return

    # confirm with react
    embed = discord.Embed(title="Add Scholar Confirmation", description=f"Confirming addition of scholar {name}/{discordUID}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Scholar Name", value=f"{name}")
    embed.add_field(name=":id: Scholar Discord ID", value=f"{discordUID}")
    embed.add_field(name=":bar_chart: Scholar Share", value=f"{round(scholarShare * 100, 2)}%")
    embed.add_field(name="Seed", value=f"{seedNum}")
    embed.add_field(name="Account", value=f"{accountNum}")
    embed.add_field(name="Address", value=f"{roninAddr}")

    if payoutAddress != "":
        embed.add_field(name="Payout Address", value=f"{payoutAddress}") 

    embed.set_footer(text="Click \N{White Heavy Check Mark} to confirm.")

    confMsg, conf = await processConfirmationAuthor(message, embed, 60)

    if conf is None:
        # timeout
        await confMsg.reply(content="You did not confirm within the timeout period, canceling!")
        return
    elif conf:
        # confirmed
        pass
    else:
        # denied/error
        await confMsg.reply(content="Canceling the request!")
        return

    # add scholar to DB
    msg = f"<@{discordId}>: \n"

    res = await DB.addScholar(discordUID, name, seedNum, accountNum, roninAddr, scholarShare)
    msg += res['msg'] + "\n"

    if payoutAddress != "":
        res2 = await DB.updateScholarAddress(discordUID, payoutAddress)
        msg += res2['msg']

    await confMsg.reply(content=msg)


# Revoke a scholar's scholar status
async def removeScholar(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isManager(authorID):
        await Common.handleResponse(message, "You must be a manager to use this command", isSlash)
        return

    if len(args) < 2:
        await Common.handleResponse(message, "Please specify: discordUID", isSlash)
        return

    discordUID = args[1]
    name = await Common.getNameFromDiscordID(discordUID)

    # confirm with react
    embed = discord.Embed(title="Remove Scholar Confirmation", description=f"Confirming removal of scholar {discordUID}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Scholar Name", value=f"{name}")
    embed.add_field(name=":id: Scholar Discord ID", value=f"{discordUID}")
    embed.set_footer(text="Click \N{White Heavy Check Mark} to confirm.")

    confMsg, conf = await processConfirmationAuthor(message, embed, 60)

    if conf is None:
        # timeout
        await confMsg.reply(content="You did not confirm within the timeout period, canceling!")
        return
    elif conf:
        # confirmed
        pass
    else:
        # denied/error
        await confMsg.reply(content="Canceling the request!")
        return

    # remove scholar from DB

    res = await DB.removeScholar(discordUID)

    await confMsg.reply(content=f"<@{discordId}>: " + res['msg'])


# Update a scholar's payout share
async def updateScholarShare(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isManager(authorID):
        await Common.handleResponse(message, "You must be a manager to use this command", isSlash)
        return

    if len(args) < 3:
        await Common.handleResponse(message, "Please specify: discordUID scholarShare", isSlash)
        return

    if not args[1].isnumeric() or not Common.isFloat(args[2]):
        await Common.handleResponse(message, "Please ensure your inputs are numbers", isSlash)
        return

    discordUID = args[1]
    scholarShare = round(float(args[2]), 3)
    name = await Common.getNameFromDiscordID(discordUID)

    if scholarShare < 0.01 or scholarShare > 1.0:
        await Common.handleResponse(message, "Please ensure your scholar share is between 0.01 and 1.00", isSlash)
        return

    res = await DB.getDiscordID(discordUID)
    user = res["rows"]
    if user is None or (user is not None and int(user["is_scholar"]) == 0):
        await Common.handleResponse(message, "Did not find a scholar with this discord ID", isSlash)
        return

    oldShare = float(user["share"])
    change = float(scholarShare) - oldShare

    if change == 0.0:
        await Common.handleResponse(message, "This is not a change, please specify a new share", isSlash)
        return

    # confirm with react
    embed = discord.Embed(title="Update Scholar Share Confirmation", description=f"Confirming update for scholar {discordUID}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Scholar Name", value=f"{name}")
    embed.add_field(name=":id: Scholar Discord ID", value=f"{discordUID}")

    if change > 0.0:
        embed.add_field(name="Change Type", value="Promotion")
    else:
        embed.add_field(name="Change Type", value="Demotion")
    embed.add_field(name="Old Share", value=f"{round(oldShare * 100, 2)}%")
    embed.add_field(name="New Share", value=f"{round(scholarShare * 100, 2)}%")
    embed.set_footer(text="Click \N{White Heavy Check Mark} to confirm.")

    confMsg, conf = await processConfirmationAuthor(message, embed, 60)

    if conf is None:
        # timeout
        await confMsg.reply(content="You did not confirm within the timeout period, canceling!")
        return
    elif conf:
        # confirmed
        pass
    else:
        # denied/error
        await confMsg.reply(content="Canceling the request!")
        return

    # update scholar share in DB

    res = await DB.updateScholarShare(discordUID, scholarShare)

    await confMsg.reply(content=f"<@{discordId}>: " + res['msg'])


# Update a scholar's login info
async def updateScholarLogin(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isManager(authorID):
        await Common.handleResponse(message, "You must be a manager to use this command", isSlash)
        return

    if len(args) < 5:
        await Common.handleResponse(message, "Please specify: discordUID address email password", isSlash)
        return

    discordUID = args[1]
    scholarAddr = args[2].replace("ronin:", "0x")
    email = args[3]
    password = args[4]
    name = await Common.getNameFromDiscordID(discordUID)

    res = await DB.getDiscordID(discordUID)
    user = res["rows"]
    if user is None or (user is not None and int(user["is_scholar"]) == 0):
        await Common.handleResponse(message, "Did not find a scholar with this discord ID", isSlash)
        return

    # confirm with react
    embed = discord.Embed(title="Update Scholar Login Info", description=f"Confirming update for scholar {discordUID}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Scholar Name", value=f"{name}")
    embed.add_field(name=":id: Scholar Discord ID", value=f"{discordUID}")
    embed.add_field(name=":house: Scholar Account Address", value=f"{scholarAddr}")
    embed.add_field(name=":email: Scholar Account Email", value=f"{email}")
    embed.add_field(name=":man_technologist: Scholar Account Password", value=f"{password}")

    embed.set_footer(text="Click \N{White Heavy Check Mark} to confirm.")

    confMsg, conf = await processConfirmationAuthor(message, embed, 60)

    if conf is None:
        # timeout
        await confMsg.reply(content="You did not confirm within the timeout period, canceling!")
        return
    elif conf:
        # confirmed
        pass
    else:
        # denied/error
        await confMsg.reply(content="Canceling the request!")
        return

    # update scholar login in DB

    res = await DB.updateScholarLogin(discordUID, scholarAddr, email, password)

    await confMsg.reply(content=f"<@{discordId}>: " + res['msg'])


async def updateScholarAddress(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id

    if len(args) < 2:
        await Common.handleResponse(message, f"Please specify: {prefix}payoutAddress", isSlash)
        return

    if len(args) > 2 and args[2].isnumeric() and isManager:
        discordId = int(args[2])

    payoutAddr = args[1].replace("ronin:","0x").strip()
    name = await Common.getNameFromDiscordID(discordId)

    if not payoutAddr.startswith("ronin:") and not payoutAddr.startswith("0x"):
        await Common.handleResponse(message, "Please ensure the payout address starts with ronin: or 0x", isSlash)
        return
 
    if not Web3.isAddress(payoutAddr):
        await Common.handleResponse(message, "That does not seem to be a valid Ronin address. Please double check it and try again.", isSlash)
        return

    res = await DB.getDiscordID(discordId)
    user = res["rows"]
    if user is None or (user is not None and (user["is_scholar"] is None or int(user["is_scholar"]) == 0)):
        await Common.handleResponse(message, "Did not find a scholar with this discord ID", isSlash)
        return

    oldAddr = user["payout_addr"]

    # confirm with react
    embed = discord.Embed(title="Update Scholar Payout Confirmation", description=f"Confirming update for scholar {discordId}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Scholar Name", value=f"{name}")
    embed.add_field(name=":id: Scholar Discord ID", value=f"{discordId}")
    embed.add_field(name="Note!", value="Please check the new address carefully!")

    embed.add_field(name="Old Address", value=f"{oldAddr}")
    embed.add_field(name="New Address", value=f"{payoutAddr}")
    embed.set_footer(text="Click \N{White Heavy Check Mark} to confirm.")

    confMsg, conf = await processConfirmationAuthor(message, embed, 60)

    if conf is None:
        # timeout
        await confMsg.reply(content="You did not confirm within the timeout period, canceling!")
        return
    elif conf:
        # confirmed
        pass
    else:
        # denied/error
        await confMsg.reply(content="Canceling the request!")
        return

    # update scholar address in DB

    res = await DB.updateScholarAddress(discordId, payoutAddr)

    await confMsg.reply(content=f"<@{authorID}>: " + res['msg'])


# Give a user manager privileges
async def addManager(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isOwner(authorID):
        await Common.handleResponse(message, "You must be the owner to use this command", isSlash)
        return

    if len(args) < 2:
        await Common.handleResponse(message, "Please specify: discordUID", isSlash)
        return

    discordUID = args[1]
    name = await Common.getNameFromDiscordID(discordUID)

    # confirm with react
    embed = discord.Embed(title="Add Manager Confirmation", description=f"Confirming adding Manager {discordUID}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Manager Name", value=f"{name}")
    embed.add_field(name=":id: Manager Discord ID", value=f"{discordUID}")
    embed.set_footer(text="Click \N{White Heavy Check Mark} to confirm.")

    confMsg, conf = await processConfirmationAuthor(message, embed, 60)

    if conf is None:
        # timeout
        await confMsg.reply(content="You did not confirm within the timeout period, canceling!")
        return
    elif conf:
        # confirmed
        pass
    else:
        # denied/error
        await confMsg.reply(content="Canceling the request!")
        return

    # add manager to DB

    res = await DB.addManager(discordUID, name)

    if res is None:
        confMsg.reply(content="Experienced unusual error, please check logs.")
        return

    await confMsg.reply(content=f"<@{authorID}>: " + res['msg'])


# Revoke a user's manager privileges
async def removeManager(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isOwner(authorID):
        await Common.handleResponse(message, "You must be the owner to use this command", isSlash)
        return

    if len(args) < 2:
        await Common.handleResponse(message, "Please specify: discordUID", isSlash)
        return

    discordUID = args[1]
    name = await Common.getNameFromDiscordID(discordUID)

    # confirm with react
    embed = discord.Embed(title="Remove Manager Confirmation", description=f"Confirming removing Manager {discordUID}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Manager Name", value=f"{name}")
    embed.add_field(name=":id: Manager Discord ID", value=f"{discordUID}")
    embed.set_footer(text="Click \N{White Heavy Check Mark} to confirm.")

    confMsg, conf = await processConfirmationAuthor(message, embed, 60)

    if conf is None:
        # timeout
        await confMsg.reply(content="You did not confirm within the timeout period, canceling!")
        return
    elif conf:
        # confirmed
        pass
    else:
        # denied/error
        await confMsg.reply(content="Canceling the request!")
        return

    # remove manager from DB
    res = await DB.removeManager(discordUID)
    await confMsg.reply(content=f"<@{authorID}>: " + res['msg'])


# Command to output a summary of user data
async def membershipCommand(message, args, isManager, discordId, guildId, isSlash=False):
    res = await DB.getMembershipReport()
    name = await Common.getNameFromDiscordID(Common.ownerID)

    embed = discord.Embed(title="Program Membership Report", description=f"Membership report for {Common.programName}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Owner Name", value=f"{name}")
    embed.add_field(name="Owner Count", value=f"{res['owner']}")
    embed.add_field(name="Manager Count", value=f"{res['managers']}")
    embed.add_field(name="Scholar Count", value=f"{res['scholars']}")
    embed.add_field(name="No Role Count", value=f"{res['noRole']}")
    embed.add_field(name="Total Users", value=f"{res['total']}")

    if isSlash:
        await message.edit(embed=embed)
    else:
        await message.reply(embed=embed)


# Helper to produce a loading bar
def getLoadingContent(complete, total):
    unixtime = int(time.time())
    disptime = str(datetime.datetime.fromtimestamp(unixtime).strftime("%H:%M:%S"))

    if massPayoutGlobal["txs"] is not None:
        scholars = massPayoutGlobal["scholarSLP"]
        manager = massPayoutGlobal["managerSLP"]
        devs = massPayoutGlobal["devSLP"]

        msg = 'Mass Payout Progress\n\n'
        msg += f"Paid to scholars: {scholars}\n"
        msg += f"Paid to manager: {manager}\n"
        msg += f"Paid to devs: {devs}\n"
    else:
        msg = 'Mass Payout Progress\n'

    msg += '\n['
    percent = (float(complete) / float(total)) * 100.0
    for i in range(1, 11):
        if i * 10 <= percent < (i + 1) * 10:
            msg += ':rocket:'
        elif percent > i * 10:
            msg += ':cloud:'
        else:
            msg += ':black_large_square:'
    msg += ':full_moon:] ({:.2f}%, {}/{})'.format(percent, complete, total)
    return msg


# Helper to live update a loading bar
massPayoutGlobal = {"counter": 0, "total": 0, "devSLP": 0, "managerSLP": 0, "scholarSLP": 0, "txs": None}


async def asyncLoadingUpdate(message):
    global massPayoutGlobal

    total = massPayoutGlobal["total"]
    lastCount = 0
    while massPayoutGlobal["counter"] <= massPayoutGlobal["total"]:
        try:
            if massPayoutGlobal["counter"] == lastCount:
                await asyncio.sleep(15)
                continue

            complete = massPayoutGlobal["counter"]
            lastCount = complete

            unixtime = int(time.time())
            disptime = str(datetime.datetime.fromtimestamp(unixtime).strftime("%H:%M:%S"))

            scholars = massPayoutGlobal["scholarSLP"]
            manager = massPayoutGlobal["managerSLP"]
            devs = massPayoutGlobal["devSLP"]

            msg = 'Mass Payout Progress\n\n'
            msg += f"Paid to scholars: {scholars}\n"
            msg += f"Paid to manager: {manager}\n"
            msg += f"Paid to devs: {devs}\n"

            msg += '\n['
            percent = (float(complete) / float(total)) * 100.0
            for i in range(1, 11):
                if i * 10 <= percent < (i + 1) * 10:
                    msg += ':rocket:'
                elif percent > i * 10:
                    msg += ':cloud:'
                else:
                    msg += ':black_large_square:'
            msg += ':full_moon:] ({:.2f}%, {}/{})'.format(percent, complete, total)

            logger.info("Updating progress/tracker message in discord")
            await message.edit(content=msg)

            if massPayoutGlobal["counter"] == massPayoutGlobal["total"]:
                logger.success("Final payout thread completed")
                break

            await asyncio.sleep(10)
        except Exception as e:
            logger.error("Exception while updating mass payout log message")
            logger.error(e)
            await asyncio.sleep(10)
    pass


# Wrapper to multi-call payouts
async def massPayoutWrapper(key, address, scholarAddress, ownerRonin, scholarShare, devDonation, discordId, name):
    global massPayoutGlobal

    try:
        res = await ClaimSLP.slpClaiming(key, address, scholarAddress, ownerRonin, scholarShare, devDonation)
    except Exception as e:
        logger.error(f"Exception thrown during claiming for {address}/{name}")
        logger.error(e)
        res = None

    if isinstance(res, int) or res is None or isinstance(res, Exception):
        logger.warning(f"Claim returned nothing for {address}/{name}")
        massPayoutGlobal["counter"] += 1
        return res
    else:
        if "scholarTx" in res and "scholarAmount" in res and res["scholarAmount"] > 0:
            if res["scholarTx"] is not None:
                massPayoutGlobal["scholarSLP"] += res["scholarAmount"]
                massPayoutGlobal["txs"].loc[len(massPayoutGlobal["txs"].index)] = [discordId, name, address, "Scholar", scholarAddress, res["scholarAmount"], "SUCCESS", res["scholarTx"]]
            else:
                massPayoutGlobal["txs"].loc[len(massPayoutGlobal["txs"].index)] = [discordId, name, address, "Scholar", scholarAddress, res["scholarAmount"], "FAILURE", None]
        if "ownerTx" in res and "ownerAmount" in res and res["ownerAmount"] > 0:
            if res["ownerTx"] is not None:
                massPayoutGlobal["managerSLP"] += res["ownerAmount"]
                massPayoutGlobal["txs"].loc[len(massPayoutGlobal["txs"].index)] = [discordId, name, address, "Owner", ownerRonin, res["ownerAmount"], "SUCCESS", res["ownerTx"]]
            else:
                massPayoutGlobal["txs"].loc[len(massPayoutGlobal["txs"].index)] = [discordId, name, address, "Owner", ownerRonin, res["ownerAmount"], "FAILURE", None]
        if "devTx" in res and "devAmount" in res and res["devAmount"] > 0:
            if res["devTx"] is not None:
                massPayoutGlobal["devSLP"] += res["devAmount"]
                massPayoutGlobal["txs"].loc[len(massPayoutGlobal["txs"].index)] = [discordId, name, address, "Devs", "0xc381c963ec026572ea82d18dacf49a1fde4a72dc", res["devAmount"], "SUCCESS", res["devTx"]]
            else:
                massPayoutGlobal["txs"].loc[len(massPayoutGlobal["txs"].index)] = [discordId, name, address, "Devs", "0xc381c963ec026572ea82d18dacf49a1fde4a72dc", res["devAmount"], "FAILURE", None]

        # DM scholar
        try:
            devTx = res["devTx"]
            ownerTx = res["ownerTx"]
            scholarTx = res["scholarTx"]
            devAmt = res["devAmount"]
            ownerAmt = res["ownerAmount"]
            scholarAmt = res["scholarAmount"]
            totalAmt = res["totalAmount"]
            claimTx = res["claimTx"]

            if not dmPayoutsToScholars or claimTx is None or totalAmt == 0:
                massPayoutGlobal["counter"] += 1
                return res

            roninTx = "https://explorer.roninchain.com/tx/"
            roninAddr = "https://explorer.roninchain.com/address/"
            embed2 = discord.Embed(title="Individual Scholar Payout Results", description=f"Data regarding the payout for {discordId}/{name}",
                                   timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())

            failedSend = ""
            if scholarTx is not None:
                embed2.add_field(name="SLP Paid to Scholar", value=f"[{scholarAmt}]({roninTx}{scholarTx})")
            else:
                failedSend += f"Scholar ({scholarAmt}), "
            if devTx is not None:
                embed2.add_field(name="SLP Donated to Devs", value=f"[{devAmt}]({roninTx}{devTx})")
            elif devAmt > 0:
                failedSend += f"Devs ({devAmt}), "
            if ownerTx is not None:
                embed2.add_field(name="SLP Paid to Manager", value=f"[{ownerAmt}]({roninTx}{ownerTx})")
            else:
                failedSend += f"Owner ({ownerAmt})"

            embed2.add_field(name="Total SLP Farmed", value=f"[{totalAmt}]({roninTx}{claimTx})")
            embed2.add_field(name="Scholar Share Paid To", value=f"[{scholarAddress}]({roninAddr}{scholarAddress})")

            if failedSend != "":
                embed2.add_field(name="Possible Failures", value=f"{failedSend}")

            logger.info(f"DMing payout info to scholar {discordId}/{name}")
            user = await Common.client.fetch_user(int(discordId))
            if user is not None:
                tm = int(time.time())
                await user.send(content=f"<t:{tm}:f> Payout Info", embed=embed2)
            else:
                logger.error(f"Failed to DM payout info to scholar {discordId}/{name}")
        except Exception as e:
            logger.error(f"Failed to DM scholar {discordId}/{name}")
            logger.error(e)

        massPayoutGlobal["counter"] += 1
        return res


# Command for an individual scholar payout
async def payoutCommand(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id

    mp = await DB.getProperty("massPay")
    if not mp["success"]:
        await Common.handleResponse(message, "Failed to query database for massPay property", isSlash)
        return
    if not isManager and mp["rows"] is not None and (mp["rows"]["realVal"] is None or int(mp["rows"]["realVal"]) != 0):
        await Common.handleResponse(message, "Individual payouts are disabled. Ask your manager to run a mass payout or to enable individual payouts.", isSlash)
        return

    res = await DB.getProperty("devDonation")
    if not res["success"]:
        await Common.handleResponse(message, "Failed to query database for devDonation property", isSlash)
        return

    devDonation = 0.0
    if res["rows"]["realVal"] is not None:
        devDonation = round(float(res["rows"]["realVal"]), 3)

    authorId = discordId
    if len(args) > 1 and args[1].isnumeric() and isManager:
        discordId = int(args[1])

    if int(discordId) in Common.payBlacklist:
        await Common.handleResponse(message, "Sorry, payouts are disabled for your account.", isSlash)
        return

    res = await DB.getDiscordID(discordId)
    user = res["rows"]
    if user is None or (user is not None and (user["is_scholar"] is None or int(user["is_scholar"]) == 0)):
        await Common.handleResponse(message, "Did not find a scholar with your discord ID", isSlash)
        return

    name = user['name']
    payoutAddr = user['payout_addr'].strip()
    share = float(user['share'])

    if payoutAddr is None or payoutAddr == "":
        await Common.handleResponse(message, f"Please set your payout address with '{prefix}setPayoutAddress ronin:...' first", isSlash)
        return

    key, address = await UtilBot.getKeyForUser(user)
    if key is None or address is None:
        await Common.handleResponse(message, "Mismatch detected between configured scholar account address and seed/account indices, or scholar not found.", isSlash)
        return

    dbClaim = await DB.getLastClaim(address)
    #print(dbClaim)
    if "success" in dbClaim and dbClaim["success"] and dbClaim["rows"] is not None and int(dbClaim["rows"]["claim_time"]) + 1209600 > time.time():
        nextT = int(dbClaim["rows"]["claim_time"]) + 1209600
        await Common.handleResponse(message, f"Sorry, your next claim isn't available yet! Please try again at <t:{nextT}:f> (<t:{nextT}:R>)", isSlash)
        return

    # logger.info(f"Scholar {discordId} account addr confirmed as {address} via mnemonic")

    # accessToken = getPlayerToken(key, address)
    # slp_data = json.loads(await ClaimSLP.getSLP(accessToken, address))
    # claimable = slp_data['claimable_total']
    # nextClaimTime = slp_data['last_claimed_item_at'] + 1209600
    # if nextClaimTime > time.time():
    #    await handleResponse(message,f"Unable to process claim for {name}; payout can be claimed <t:{nextClaimTime}:R>.", isSlash)
    #    return
    # if claimable == 0:
    #    await handleResponse(message,f"Unable to process claim for {name}; payout can be claimed <t:{nextClaimTime}:R> but there is no claimable SLP.", isSlash)
    #    return

    # confirm with react
    embed = discord.Embed(title="Individual Scholar Payout Confirmation", description=f"Confirming payout for {name}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name="Scholar Name", value=f"{name}")
    embed.add_field(name="Scholar Discord ID", value=f"{discordId}")
    embed.add_field(name="Scholar Share", value=f"{round(share * 100, 3)}")
    embed.add_field(name="Payout Address", value=f"{payoutAddr}")
    embed.add_field(name="Note", value="Please carefully check the payout address! Misplaced SLP cannot be recovered!")

    embed.set_footer(text="Click \N{White Heavy Check Mark} to confirm.")

    confMsg, conf = await processConfirmationAuthor(message, embed, 60)

    if conf is None:
        # timeout
        await confMsg.reply(content="You did not confirm within the timeout period, canceling!")
        return
    elif conf:
        # confirmed
        pass
    else:
        # denied/error
        await confMsg.reply(content="Canceling the request!")
        return

    processMsg = await confMsg.reply(content=f"Processing your payout <@{discordId}>... this may take up to a couple minutes. Please be patient.")

    try:
        # devSlp, ownerSlp, scholarSlp = ClaimSLP.slpClaiming(key, address, payoutAddr, ownerRonin, share, devDonation)
        claimRes = await ClaimSLP.slpClaiming(key, address, payoutAddr, Common.ownerRonin, share, devDonation)
    except Exception as e:
        logger.error(e)
        if authorId == discordId:
            await processMsg.reply(content=f"<@{discordId}> there was an error while processing your payout. Please work with your manager to have it manually resolved.")
        else:
            await processMsg.reply(content=f"<@{authorId}> there was an error while processing the payout.")
        return

    if isinstance(claimRes, int):
        if authorId == discordId:
            await processMsg.reply(content=f"<@{authorID}>: your account is available to claim <t:{claimRes}:R> at <t:{claimRes}:f>.")
        else:
            await processMsg.reply(content=f"<@{authorID}>: {name}'s account is available to claim <t:{claimRes}:R> at <t:{claimRes}:f>.")
        return

    if claimRes is None:
        await processMsg.reply(content=f"<@{discordId}> there was an error while processing your payout. Please ask your manager if you should try again.")
        return

    devTx = claimRes["devTx"]
    ownerTx = claimRes["ownerTx"]
    scholarTx = claimRes["scholarTx"]
    devAmt = claimRes["devAmount"]
    ownerAmt = claimRes["ownerAmount"]
    scholarAmt = claimRes["scholarAmount"]
    totalAmt = claimRes["totalAmount"]
    claimTx = claimRes["claimTx"]

    if totalAmt == 0:
        await processMsg.reply(content=f"<@{discordId}> there was no SLP to claim.")
        return

    roninTx = "https://explorer.roninchain.com/tx/"
    roninAddr = "https://explorer.roninchain.com/address/"
    embed2 = discord.Embed(title="Individual Scholar Payout Results", description=f"Data regarding the payout for {discordId}/{name}",
                           timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())

    failedSend = ""
    if scholarTx is not None:
        embed2.add_field(name="SLP Paid to Scholar", value=f"[{scholarAmt}]({roninTx}{scholarTx})")
    else:
        failedSend += f"Scholar ({scholarAmt}), "
    if devTx is not None:
        embed2.add_field(name="SLP Donated to Devs", value=f"[{devAmt}]({roninTx}{devTx})")
    elif devAmt > 0:
        failedSend += f"Devs ({devAmt}), "
    if ownerTx is not None:
        embed2.add_field(name="SLP Paid to Manager", value=f"[{ownerAmt}]({roninTx}{ownerTx})")
    else:
        failedSend += f"Owner ({ownerAmt})"

    embed2.add_field(name="Total SLP Farmed", value=f"[{totalAmt}]({roninTx}{claimTx})")
    embed2.add_field(name="Scholar Share Paid To", value=f"[{payoutAddr}]({roninAddr}{payoutAddr})")

    if failedSend != "":
        embed2.add_field(name="Possible Failures", value=f"{failedSend}")

    if dmPayoutsToScholars:
        logger.warning("DMing payout info to scholar: " + str(discordId))
        user = await Common.client.fetch_user(int(discordId))
        if user is not None:
            tm = int(time.time())
            await user.send(content=f"<t:{tm}:f> Payout Info", embed=embed2)
        else:
            logger.error("Failed to DM payout info to scholar: " + str(discordId))

    await processMsg.reply(content=f"<@{authorID}>", embed=embed2)


# Command to payout all scholars
async def payoutAllScholars(message, args, isManager, discordId, guildId, isSlash=False):
    global massPayoutGlobal

    if massPayoutGlobal["total"] > 0:
        await Common.handleResponse(message, "Mass payout already running", isSlash)
        return

    massPayoutGlobal = {"counter": 0, "total": 0, "devSLP": 0, "managerSLP": 0, "scholarSLP": 0, "txs": pd.DataFrame(columns=["DiscordID", "DiscordName", "ScholarAddress", "Target", "Address", "Amount", "Status", "Hash"])}

    authorID = message.author.id
    if not await DB.isManager(authorID):
        await Common.handleResponse(message, "You must be a manager to use this command", isSlash)
        return

    if len(args) >= 4:
        try:
            seedNum = int(args[1])
            minIndex = int(args[2])
            maxIndex = int(args[3])
        except:
            logger.warning("Invalid seed/account index range for mass payout")
            await Common.handleResponse(message, "Invalid seed/account index range for mass payout", isSlash)
            return
    elif len(args) == 2:
        try:
            seedNum = int(args[1])
            minIndex = None
            maxIndex = None
        except:
            logger.warning("Invalid seed number for mass payout")
            await Common.handleResponse(message, "Invalid seed number for mass payout", isSlash)
            return
    else:
        seedNum = None
        minIndex = None
        maxIndex = None

    if seedNum is None:
        scholarsDB = await DB.getAllScholars()
    elif minIndex is None or maxIndex is None:
        scholarsDB = await DB.getAllScholarsByIndex(seedNum)
    else:
        scholarsDB = await DB.getAllScholarsByIndex(seedNum, minIndex, maxIndex)
    if not scholarsDB["success"]:
        await Common.handleResponse(message, "Failed to query database for scholars", isSlash)
        return
    scholarCount = len(scholarsDB['rows'])

    res = await DB.getProperty("devDonation")
    if not res["success"]:
        await Common.handleResponse(message, "Failed to query database for devDonation property", isSlash)
        return

    devDonation = 0.0
    if res["rows"]["realVal"] is not None:
        devDonation = round(float(res["rows"]["realVal"]), 3)

    mp = await DB.getProperty("massPay")
    if not mp["success"]:
        await Common.handleResponse(message, "Failed to query database for massPay property", isSlash)
        return

    # confirm with react
    embed = discord.Embed(title="Mass Scholar Payout Confirmation", description=f"Confirming mass payout of scholars",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name="Scholar Count", value=f"{scholarCount}")

    if seedNum is not None:
        embed.add_field(name="Filtered for Seed", value=f"{seedNum}")
    if minIndex is not None and maxIndex is not None:
        embed.add_field(name="Filtered for Index Range", value=f"{minIndex}-{maxIndex}")

    if mp["rows"] is not None and (mp["rows"]["realVal"] is None or int(mp["rows"]["realVal"]) == 0):
        embed.add_field(name="Note", value=f"Running a mass payment will disable individual payments. You will have to re-enable them later with '{prefix}setProperty massPay 0'")

    embed.set_footer(text="Click \N{White Heavy Check Mark} to confirm.")

    confMsg, conf = await processConfirmationAuthor(message, embed, 60)

    if conf is None:
        # timeout
        await confMsg.reply(content="You did not confirm within the timeout period, canceling!")
        return
    elif conf:
        # confirmed
        await DB.setProperty("massPay", 1)
    else:
        # denied/error
        await confMsg.reply(content="Canceling the request!")
        return

    msg = getLoadingContent(0, scholarCount)
    loadMsg = await confMsg.reply(content=msg)

    massPayoutGlobal["total"] = scholarCount

    skipped = 0
    processed = 0

    calls = []

    for row in scholarsDB["rows"]:
        try:
            scholarID = row['discord_id']

            if int(scholarID) in Common.payBlacklist:
                skipped += 1
                continue

            key, address = await UtilBot.getKeyForUser(row)
            if key is None or address is None:
                skipped += 1
                continue

            dbClaim = await DB.getLastClaim(address)
            if "success" in dbClaim and dbClaim["success"] and dbClaim["rows"] is not None and int(dbClaim["rows"]["claim_time"]) + 1209600 > time.time():
                skipped += 1
                continue

            # logger.info(f"Scholar {discordId} account addr confirmed as {address} via mnemonic")

            name = row["name"].strip()
            #name = await Common.getNameFromDiscordID(scholarID)
            scholarAddress = row['payout_addr'].replace("ronin:","0x").strip()
            scholarShare = round(float(row['share']), 3)

            if scholarAddress is None or scholarAddress == "" or not Web3.isAddress(scholarAddress):
                skipped += 1
                continue

            # accessToken = getPlayerToken(key, address)
            # slp_data = json.loads(await ClaimSLP.getSLP(accessToken, address))
            # claimable = slp_data['claimable_total']
            # nextClaimTime = slp_data['last_claimed_item_at'] + 1209600
            # if claimable == 0 or nextClaimTime > time.time():
            #    skipped += 1
            #    continue

            calls.append(massPayoutWrapper(key, address, scholarAddress, Common.ownerRonin, scholarShare, devDonation, scholarID, name))
        except Exception as e:
            skipped += 1
            logger.error(f"Failed to queue claim for a scholar {scholarID} (skipping), not logging because private key is involved")
            # logger.error(traceback.format_exc())

    massPayoutGlobal["counter"] = skipped
    out = await asyncio.gather(asyncLoadingUpdate(loadMsg), *calls, return_exceptions=True)

    msg = getLoadingContent(scholarCount, scholarCount)
    await loadMsg.edit(content=msg)

    devTotal = massPayoutGlobal["devSLP"]
    ownerTotal = massPayoutGlobal["managerSLP"]
    scholarTotal = massPayoutGlobal["scholarSLP"]

    grandTotal = devTotal + ownerTotal + scholarTotal

    for entry in out[1:]:
        if entry is None or isinstance(entry, int) or isinstance(entry, Exception) or ("totalAmount" in entry and entry["totalAmount"] == 0):
            skipped += 1
        else:
            processed += 1

    embed2 = discord.Embed(title="All Scholar Payout Results", description=f"Data regarding the mass payout",
                           timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed2.add_field(name="Scholars Paid", value=f"{processed}")
    embed2.add_field(name="Scholars Skipped/Not Ready", value=f"{skipped}")
    embed2.add_field(name="SLP Paid to Scholars", value=f"{scholarTotal}")
    embed2.add_field(name="SLP Donated to Devs", value=f"{devTotal}")
    embed2.add_field(name="SLP Paid to Manager", value=f"{ownerTotal}")
    embed2.add_field(name="Total SLP Farmed", value=f"{grandTotal}")

    fName = "massPayoutTxs.csv"
    massPayoutGlobal["txs"].to_csv(fName, index=False)
    massPayoutGlobal["total"] = 0

    await loadMsg.reply(content=f"<@{authorID}>", embed=embed2, file=discord.File(fName))


# Command to get a daily summary for a scholar
async def dailyCommand(message, args, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()

        # check if they're a valid scholar
    author = await DB.getDiscordID(message.author.id)
    if (author["success"] and author["rows"]["is_scholar"]) or isManager:
        # check if the request is for someone else's data
        tId = discordId
        if not isSlash and len(message.mentions) > 0:
            tId = message.mentions[0].id
            targ = await DB.getDiscordID(tId)
            if targ["success"]:
                targ = targ["rows"]
                tId = targ["discord_id"]
            else:
                tId = message.author.id
                targ = author["rows"]

        elif len(args) > 1 and len(args[1].strip()) > 0 and UtilBot.is_int(args[1].strip()):
            targ = await DB.getDiscordID(args[1])
            if targ["success"]:
                targ = targ["rows"]
                tId = targ["discord_id"]
            else:
                tId = message.author.id
                targ = author["rows"]

        elif len(args) > 1 and len(args[1].strip()) > 0:
            scholarsDB = await DB.getAllScholars()
            if not scholarsDB["success"]:
                await Common.handleResponse(message, "Failed to query database for scholars", isSlash)
                return
            scholarCount = len(scholarsDB['rows'])
            tId = message.author.id
            targ = author["rows"]

            search = args[1].strip().lower()

            for r in scholarsDB["rows"]:
                if r["name"].lower().startswith(search):
                    targ = r
                    tId = targ["discord_id"]
                    break

        else:
            tId = message.author.id
            targ = author["rows"]

        roninKey, roninAddr = await UtilBot.getKeyForUser(targ)
        if roninKey is None or roninAddr is None:
            await Common.handleResponse(message, "Mismatch detected between configured scholar account address and seed/account indices, or scholar not found.", isSlash)
            return

        logger.info(f"Scholar {discordId} account addr confirmed as {roninAddr} via mnemonic")

        if roninAddr == "" or roninKey == "":
            msg = 'Sorry <@' + str(discordId) + '>, your manager has not configured game data access.'
            await Common.handleResponse(message, msg, isSlash)
            return

        # fetch data
        res = await UtilBot.getPlayerDailies(discordId, tId, targ["name"], roninKey, roninAddr, guildId)

        if res is None:
            msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error fetching your stats. Please try again later.'
            await Common.handleResponse(message, msg, isSlash)
            return

        # send results
        # await message.channel.send(res["msg"])
        if isSlash:
            await message.edit(embed=res["embed"])
        else:
            await message.reply(embed=res["embed"])

    else:
        msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + Common.programName + '\'s scholars.'
        await Common.handleResponse(message, msg, isSlash)

    return


# Command to get recent battles summary for an address or scholar
async def battlesCommand(message, args, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()

    if len(args) > 1 and (args[1].startswith("0x") or args[1].startswith("ronin:")):
        roninAddr = args[1].replace("ronin:", "0x")

        # fetch data
        res = await UtilBot.getRoninBattles(roninAddr)

        if res is None:
            msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error fetching the battles, or there are 0 battles to fetch. Please try again later.'
            await Common.handleResponse(message, msg, isSlash)
            return

        # send results
        # await message.channel.send(res["msg"])
        if res['image'] is None:
            if isSlash:
                await message.edit(embed=res["embed"])
            else:
                await message.reply(embed=res["embed"])
        else:
            combinedFile = discord.File(res['image'])
            if isSlash:
                await message.edit(embed=res["embed"])  # file=combinedFile
            else:
                await message.reply(file=combinedFile, embed=res["embed"])

    else:
        # check if they're a valid scholar
        author = await DB.getDiscordID(message.author.id)
        if (author["success"] and author["rows"]["is_scholar"]) or isManager:

            # check if the request is for someone else's data
            tId = discordId
            if len(args) > 1 and len(args[1].strip()) > 0:
                targ = await DB.getDiscordID(args[1])
                if targ["success"]:
                    targ = targ["rows"]
                    tId = targ["discord_id"]
                else:
                    targ = author["rows"]
            else:
                targ = author["rows"]

            roninKey, roninAddr = await UtilBot.getKeyForUser(targ)
            if roninKey is None or roninAddr is None:
                await Common.handleResponse(message, "Mismatch detected between configured scholar account address and seed/account indices, or scholar not found.", isSlash)
                return

            logger.info(f"Scholar {discordId} account addr confirmed as {roninAddr} via mnemonic")

            if roninAddr == "":
                msg = 'Sorry <@' + str(discordId) + '>, your manager has not configured game data access.'
                await Common.handleResponse(message, msg, isSlash)
                return

            # fetch data
            res = await UtilBot.getScholarBattles(discordId, tId, targ["name"], roninAddr)

            if res is None:
                msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error fetching your battles, or there are 0 battles to fetch. Please try again later.'
                await Common.handleResponse(message, msg, isSlash)
                return

            # send results
            # await message.channel.send(res["msg"])
            if res['image'] is None:
                if isSlash:
                    await message.edit(embed=res["embed"])
                else:
                    await message.reply(embed=res["embed"])
            else:
                combinedFile = discord.File(res['image'])
                if isSlash:
                    await message.edit(embed=res["embed"])  # file=combinedFile
                else:
                    await message.reply(file=combinedFile, embed=res["embed"])
        else:
            msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + Common.programName + '\'s scholars.'
            await Common.handleResponse(message, msg, isSlash)

        return


# Command to get a scholar's axie team information
async def axiesCommand(message, args, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()

        # check if user is a valid scholar
    author = await DB.getDiscordID(message.author.id)
    if (author["success"] and author["rows"]["is_scholar"]) or isManager:
        # check if the request is for someone else's data
        tId = discordId
        if not isSlash and len(message.mentions) > 0:
            tId = message.mentions[0].id
            targ = await DB.getDiscordID(tId)
            if targ["success"]:
                targ = targ["rows"]
                tId = targ["discord_id"]
            else:
                tId = message.author.id
                targ = author["rows"]

        elif len(args) > 1 and len(args[1].strip()) > 0 and UtilBot.is_int(args[1].strip()):
            targ = await DB.getDiscordID(args[1])
            if targ["success"]:
                targ = targ["rows"]
                tId = targ["discord_id"]
            else:
                tId = message.author.id
                targ = author["rows"]

        elif len(args) > 1 and len(args[1].strip()) > 0:
            scholarsDB = await DB.getAllScholars()
            if not scholarsDB["success"]:
                await Common.handleResponse(message, "Failed to query database for scholars", isSlash)
                return
            scholarCount = len(scholarsDB['rows'])
            tId = message.author.id
            targ = author["rows"]

            search = args[1].strip().lower()

            for r in scholarsDB["rows"]:
                if r["name"].lower().startswith(search):
                    targ = r
                    tId = targ["discord_id"]
                    break

        else:
            tId = message.author.id
            targ = author["rows"]

        roninKey, roninAddr = await UtilBot.getKeyForUser(targ)
        if roninKey is None or roninAddr is None:
            await Common.handleResponse(message, "Mismatch detected between configured scholar account address and seed/account indices, or scholar not found.", isSlash)
            return

        logger.info(f"Scholar {discordId} account addr confirmed as {roninAddr} via mnemonic")

        ind = -1
        if len(args) > 2 and args[2].isnumeric():
            ind = int(args[2])

        mobile = 0
        if len(args) > 3 and (args[3] == "1" or args[3].lower() == "m"):
            mobile = 1

        # fetch axie data
        res = await UtilBot.getPlayerAxies(tId, targ["name"], roninKey, roninAddr, ind)

        if res is None:
            msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error fetching your axies. Please try again later.'
            await Common.handleResponse(message, msg, isSlash)
            return

        # send results
        embed = None
        if mobile == 0:
            embed = res["embed"]
        else:
            embed = res["mobileEmbed"]

        if res['image'] is None:
            if isSlash:
                await message.edit(embed=embed)
            else:
                await message.reply(embed=embed)
            return
        else:
            combinedFile = discord.File(res['image'])
            if isSlash:
                await message.edit(embed=embed)  # file=combinedFile
            else:
                await message.reply(file=combinedFile, embed=embed)

    else:
        msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + Common.programName + '\'s scholars.'
        await Common.handleResponse(message, msg, isSlash)

    return


# Command to get a summary of all scholars
async def summaryCommand(message, args, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()

    # check for sorting instructions
    sort = "avgSlp"
    asc = False
    ascText = "desc"
    if len(args) > 1 and args[1].lower() in ["claim", "avgslp", "slp", "mmr", "adventure", "adv", "arena", "rank", "battle"]:
        sort = args[1].lower()

    if len(args) > 2 and args[2].lower() in ["asc", "desc"]:
        if args[2].lower() == "asc":
            asc = True
            ascText = "asc"

    csv = False
    if len(args) > 3 and str(args[3]).lower() in ["1","true","yes","csv"]:
        csv = True

    # fetch the data
    table, cacheExp = await UtilBot.getScholarSummary(sort.lower(), asc, guildId)

    # error
    if table is None or cacheExp is None:
        msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error building the summary. Please try again later.'
        if isSlash:
            await message.edit(content=msg)
        else:
            await message.reply(msg)
        return

    # send results
    msg = 'Hello <@' + str(discordId) + '>, here is the scholar summary sorted by `' + sort + " " + ascText + "`:"

    if not csv:
        logger.info("Preparing summary image")
        fig = go.Figure(data=[go.Table(
            columnwidth=[75, 400, 100, 200, 150, 200, 150, 150, 150, 150, 100, 200],
            header=dict(values=list(table.columns),
                        fill_color="paleturquoise",
                        align='center'),
            cells=dict(values=table.T.values,
                       fill_color='lavender',
                       align='center'))
        ])
        fig.update_layout(margin=dict(
            l=0,  # left margin
            r=0,  # right margin
            b=0,  # bottom margin
            t=0  # top margin
        ))
        fName = os.getcwd() + '/images/summary' + str(int(time.time())) + '.png'
        fig.write_image(fName, width=1200, height=20 * len(table) + 30)
    else:
        logger.info("Preparing summary spreadsheet")
        fName = 'images/summary' + str(int(time.time())) + '.csv'
        table.to_csv(fName, index=False)

    if isSlash:
        await message.edit(content=msg)
        await message.followup(file=discord.File(fName))
    else:
        await message.reply(content=msg, file=discord.File(fName))

    logger.info("Sent summary")
    os.remove(fName)


async def exportCommand(message, isManager, isSlash=False):
    if not isManager:
        await message.reply("Sorry, this command is only for managers!")
        return

    df = await UtilBot.getScholarExport()
    df.to_csv("export.csv", index=False)

    if isSlash:
        await message.channel.send(file=discord.File('export.csv'))
    else:
        await message.reply(file=discord.File('export.csv'))
    os.remove("export.csv")


# Command to get a top 10 summary of all scholars
async def topCommand(message, args, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()

        # check for sorting instructions
    sort = "mmr"
    asc = False
    ascText = "desc"
    if len(args) > 1 and args[1].lower() in ["avgslp", "slp", "mmr", "adventure", "adv", "arena", "rank", "battle"]:
        sort = args[1].lower()

    csv = False
    if len(args) > 2 and str(args[2]).lower() in ["1","true","yes","csv"]:
        csv = True

    # fetch the data
    table, cacheExp = await UtilBot.getScholarTop10(sort.lower())

    # error
    if table is None or cacheExp is None:
        msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error building the top 10. Please try again later.'
        if isSlash:
            await message.edit(content=msg)
        else:
            await message.reply(msg)
        return

    # send results
    msg = 'Hello <@' + str(discordId) + '>, here is the scholar top 10 sorted by `' + sort + " " + ascText + "`:"

    if not csv:
        logger.info("Preparing top10 image")
        fig = go.Figure(data=[go.Table(
            columnwidth=[75, 400, 100, 200, 150, 200, 150, 150, 150, 150, 100, 200],
            header=dict(values=list(table.columns),
                        fill_color="paleturquoise",
                        align='center'),
            cells=dict(values=table.T.values,
                       fill_color='lavender',
                       align='center'))
        ])
        fig.update_layout(margin=dict(
            l=0,  # left margin
            r=0,  # right margin
            b=0,  # bottom margin
            t=0  # top margin
        ))
        fName = os.getcwd() + '/images/top' + str(int(time.time())) + '.png'
        fig.write_image(fName, width=1200, height=20 * len(table) + 30)
    else:
        logger.info("Preparing top10 spreadsheet")
        fName = 'images/top' + str(int(time.time())) + '.csv'
        table.to_csv(fName, index=False)

    if isSlash:
        await message.edit(content=msg)
        await message.followup(file=discord.File(fName))
    else:
        await message.reply(content=msg, file=discord.File(fName))

    os.remove(fName)


async def alertsCommand(message, args, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()

    ping = False
    if len(args) > 1 and args[1] == "1":
        ping = True

    rn = datetime.datetime.now(datetime.timezone.utc)
    logger.info(f"Processing on-demand alert, ping={ping}")

    if isSlash:
        await message.edit(content="Processing!")
    else:
        await message.reply("Processing!")

    await UtilBot.nearResetAlerts(rn, True, ping)

async def wipeClaims(message, isManager, discordId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()

    if not isManager:
        await message.reply("Sorry, managers only.")
        return       

    res = await DB.wipeClaimLogs()

    if res["success"]:
        await message.reply("Wiped the claim logs!")
    else:
        await message.reply("Failed to wipe the claim logs.")

