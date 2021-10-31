# Author: Michael Conard
# Purpose: An Axie Infinity utility bot. Gives QR codes and daily progress/alerts.

import discord
import os
import traceback
import math
import configparser
import json
import datetime
import asyncio
import time
import pandas as pd
from pandas.plotting import table as tableTool
import plotly.graph_objects as go
from discord.ext import tasks, commands

from SecretStorage import *
from Common import *
from UtilBot import *
import DB
import ClaimSLP


async def helpCommand(message, discordId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()     

    msg = 'Hello <@' + str(discordId) + '>! Here are the available commands:\n'
    msg += ' - `' + prefix + 'help`: returns this help message\n'
    msg += ' - `' + prefix + 'qr`: DMs you your QR code to login\n'
    msg += ' - `' + prefix + 'daily [name]`: returns the player\'s match/SLP/quest data for today\n'
    msg += ' - `' + prefix + 'axies [name] [index] [m]`: returns the player\'s Axies, [index] is to select a team (default 0), set [m] for mobile friendly\n'
    msg += ' - `' + prefix + 'battles [name]`: returns the scholar\'s recent battle records\n'
    msg += ' - `' + prefix + 'summary [sort] [ascending]`: returns a scholar summary, [avgslp/slp, mmr/rank, claim], [asc, desc]\n'
    msg += ' - `' + prefix + 'export`: returns a listing of scholar information\n'
    msg += ' - `' + prefix + 'getScholar [discordID]`: returns information on the caller, or the specified discord ID\n'
    msg += ' - `' + prefix + 'addScholar seedNum accountNum discordID [scholarShare]`: add a scholar to the database; scholar share is 0.01 to 1.00\n'
    msg += ' - `' + prefix + 'removeScholar discordID`: removes the user\'s status as a scholar\n'
    msg += ' - `' + prefix + 'addManager discordID`: add a manager to the database\n'
    msg += ' - `' + prefix + 'removeManager discordID`: removes the user\'s status as a manager\n'
    msg += ' - `' + prefix + 'updateScholarShare discordID scholarShare`: sets the user\'s share to the new value, 0.01 to 1.00\n'
    msg += ' - `' + prefix + 'setPayoutAddress roninAddress`: sets the caller\'s payout address, can be ronin: or 0x form\n'
    msg += ' - `' + prefix + 'membership`: returns information about the status of the user database\n'
    msg += ' - `' + prefix + 'setProperty property value`: sets a property to a value\n'
    msg += ' - `' + prefix + 'getProperty property`: gets a property\'s value (try "devDonation")\n'
    msg += ' - `' + prefix + 'massPayout`: triggers a scholar payout for all scholars\n'
    msg += ' - `' + prefix + 'payout`: triggers a payout just for you (the caller)\n'
    
    await handleResponse(message,msg,isSlash)
    return


async def qrCommand(message, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()     
    
    if os.path.exists("./qr/" + str(message.author.id)+"QRCode.png"):
        os.remove("./qr/" + str(message.author.id)+"QRCode.png")

    current_time = datetime.datetime.now().strftime("%H:%M:%S")

    # check for user's Discord ID
    if message.author.id in qrBlacklist:
        msg = "Sorry, but QR generation isn't working for your account right now. Please talk to your manager."
        message.author.send(msg)

        if guildId is not None:
            msg = 'Hi <@' + str(discordId) + '>, please check your DMs!'
            await handleResponse(message,msg,isSlash)

        return

    if str(message.author.id) in ScholarsDict:
        logger.info("This user received their QR Code : " + message.author.name)

        scholar = ScholarsDict[str(message.author.id)]

        # discordID's privateKey
        accountPrivateKey = scholar[2]
        # discordID's address
        accountAddress = scholar[1]

        if accountPrivateKey == "" or accountAddress == "":
            msg = 'Sorry <@' + str(discordId) + '>, your manager has not configured QR code generation.'
            await handleResponse(message,msg,isSlash)
            return

        accessToken = getPlayerToken(accountPrivateKey, accountAddress)

        if accessToken is None:
            msg = 'Sorry <@' + str(discordId) + '>, there was an issue with your request. Please try again later.'
            await handleResponse(message,msg,isSlash)
            return

        # Create a QrCode with that accessToken
        qrFileName = getQRCode(accessToken, message.author.id)

        # Send the QrCode the the user who asked for
        await message.author.send(
            "------------------------------------------------\n\n\nHello " + message.author.name + "\nHere is your new QR Code to login: ")
        await message.author.send(file=discord.File(qrFileName))
        await message.author.send("Remember to keep your QR code safe and don't let anyone else see it!")

        if guildId is not None:
            msg = 'Hi <@' + str(discordId) + '>, please check your DMs!'
            await handleResponse(message,msg,isSlash)

        return

    else:
        logger.warning("This user didn't receive a QR Code : " + message.author.name)
        msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + programName + '\'s scholars.'
        
        await handleResponse(message,msg,isSlash)
        return


async def setPropertyCommand(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isManager(authorID):
        await handleResponse(message,"You must be a manager to use this command",isSlash)
        return            

    if len(args) < 3:
        await handleResponse(message,"Please enter: &setProperty property value",isSlash)
        return

    prop = args[1]
    val = args[2]
    
    res = await DB.setProperty(prop, val)
    await handleResponse(message,res["msg"],isSlash)


async def getPropertyCommand(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id

    if len(args) < 2:
        await handleResponse(message,"Please enter: &getProperty property",isSlash)
        return

    prop = args[1]
    
    res = await DB.getProperty(prop)

    if not res["success"] or (res["success"] and res["rows"] is None):
        await handleResponse(message,f"Failed to get property {prop}",isSlash)
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


def getEmojiFromReact(reaction):
    emoji = None
    if type(reaction.emoji) is str:
        emoji = reaction.emoji
    else:
        emoji = reaction.emoji.name
    return emoji


async def processConfirmationAuthor(message, embed, timeoutSecs=None):
    authorID = message.author.id
    confMsg = await message.reply(embed=embed)
    
    greenCheck = "\N{White Heavy Check Mark}"
    redX = "\N{Cross Mark}"
    options = [greenCheck, redX]

    await confMsg.add_reaction(greenCheck)
    await confMsg.add_reaction(redX)

    def check(reaction, user):
        emoji = getEmojiFromReact(reaction)
        return int(user.id) == int(authorID) and emoji in options and int(reaction.message.id) == int(confMsg.id)

    try:
        reaction, user = await client.wait_for('reaction_add', timeout=timeoutSecs, check=check)
        emoji = getEmojiFromReact(reaction)
        if emoji == greenCheck:
            return confMsg, True
        elif emoji == redX:
            return confMsg, False
        else:
            return confMsg, None
    
    except asyncio.TimeoutError:
        return confMsg, None


async def processConfirmationManager(message, embed, timeoutSecs=None):
    authorID = message.author.id
    mgrIds = await DB.getAllManagerIDs()

    confMsg = await message.reply(embed=embed)
    
    greenCheck = "\N{White Heavy Check Mark}"
    redX = "\N{Cross Mark}"
    options = [greenCheck, redX]

    await confMsg.add_reaction(greenCheck)
    await confMsg.add_reaction(redX)

    def check(reaction, user):
        emoji = getEmojiFromReact(reaction)
        return user.id in mgrIds and emoji in options and reaction.message == confMsg

    try:
        reaction, user = await client.wait_for('reaction_add', timeout=timeoutSecs, check=check)
        emoji = getEmojiFromReact(reaction)
        if emoji == greenCheck:
            return confMsg, True
        elif emoji == redX:
            return confMsg, False
        else:
            return confMsg, None
    
    except asyncio.TimeoutError:
        return confMsg, None


async def getScholar(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id

    if len(args) > 1 and not args[1].isnumeric():
        await handleResponse(message,"Please ensure the discord ID is correct",isSlash)
        return    
    if len(args) > 1:
        discordId = int(args[1])    
    
    name = await getNameFromDiscordID(discordId)
    if name is None:
        await handleResponse(message,"Could not find user with that discord ID",isSlash)
        return    

    scholarRes = await DB.getDiscordID(discordId)
    if not scholarRes["success"]:
        await handleResponse(message,"Failed to get scholar from database",isSlash)
        return
    if scholarRes["rows"]["is_scholar"] is None or scholarRes["rows"]["is_scholar"] == 0:
        await handleResponse(message,f"Did not find a scholar with discord ID {discordId}",isSlash)
        return
 
    scholar = scholarRes["rows"]
    scholarShare = round(float(scholar["share"]),3)
    scholarAddr = scholar["payout_addr"]
    seedNum = scholar["seed_num"]
    accountNum = scholar["account_num"]
    createdTime = scholar["created_at"]
    scholarDate = datetime.datetime.fromtimestamp(int(createdTime)).strftime('%Y-%m-%d %H:%M:%S') 

    if hideScholarRonins:
        roninAddr = "<hidden>"
    else:
        roninAddr = ScholarsDict[str(discordId)][1]

    embed = discord.Embed(title="Scholar Information", description=f"Information about scholar {name}/{discordId}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Scholar Name", value=f"{name}")
    embed.add_field(name=":id: Scholar Discord ID", value=f"{discordId}")
    embed.add_field(name=":bar_chart: Scholar Share", value=f"{round(scholarShare*100,2)}%")
    embed.add_field(name=":clock1: Scholar Created", value=f"{scholarDate}")
    embed.add_field(name="Seed", value=f"{seedNum}")
    embed.add_field(name="Account", value=f"{accountNum}")
    embed.add_field(name="Account Address", value=f"{roninAddr}")
    embed.add_field(name="Payout Address", value=f"{scholarAddr}")

    if isSlash:
        await message.edit(content=f"<@{authorID}>", embed=embed)
    else:
        await message.reply(content=f"<@{authorID}>", embed=embed)


async def addScholar(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isManager(authorID):
        await handleResponse(message,"You must be a manager to use this command",isSlash)
        return

    if len(args) < 4:
        await handleResponse(message,"Please specify: seedNum accountNum discordUID [scholarShare]",isSlash)
        return            

    seedNum = args[1]
    accountNum = args[2]
    discordUID = args[3]
    payoutAddress = ""
    scholarShare = 0.5 # pull from default config

    if (not seedNum.isnumeric() or int(seedNum) < 1) or (not accountNum.isnumeric() or int(accountNum) < 1) or not discordUID.isnumeric():
        await handleResponse(message,"Please ensure your seed/account indices are >= 1 and the discord ID is correct",isSlash)
        return    
    
    name = await getNameFromDiscordID(discordUID)
    if name is None:
        await handleResponse(message,"Could not find user with that discord ID",isSlash)
        return

    if len(args) == 5 and isFloat(args[4]):
        scholarShare = round(float(args[4]),3)
    
    if scholarShare < 0.01 or scholarShare > 1.0:
        await handleResponse(message,"Please ensure your scholar share is between 0.01 and 1.00",isSlash)
        return
    
    scholarsDB = await DB.getAllScholars()
    if not scholarsDB["success"]:
        await handleResponse(message,"Failed to query database for scholars",isSlash)
        return
 
    for scholar in scholarsDB["rows"]:
        seedNum2 = int(scholar["seed_num"])
        accNum2 = int(scholar["account_num"])

        if int(seedNum) == seedNum2 and accNum2 == int(accountNum):
            await handleResponse(message,"A scholar already exists with that seed/account pair",isSlash)
            return

    # confirm with react
    embed = discord.Embed(title="Add Scholar Confirmation", description=f"Confirming addition of scholar {name}/{discordUID}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Scholar Name", value=f"{name}")
    embed.add_field(name=":id: Scholar Discord ID", value=f"{discordUID}")
    embed.add_field(name=":bar_chart: Scholar Share", value=f"{round(scholarShare*100,2)}%")
    embed.add_field(name="Seed", value=f"{seedNum}")
    embed.add_field(name="Account", value=f"{accountNum}")

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
    
    res = await DB.addScholar(discordUID, name, seedNum, accountNum, scholarShare)
    
    await confMsg.reply(content=f"<@{discordId}>: " + res['msg'])


async def removeScholar(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isManager(authorID):
        await handleResponse(message,"You must be a manager to use this command",isSlash)
        return            
    
    if len(args) < 2:
        await handleResponse(message,"Please specify: discordUID",isSlash)
        return

    discordUID = args[1]
    name = await getNameFromDiscordID(discordUID)

    # confirm with react
    embed = discord.Embed(title="Remove Scholar Confirmation", description=f"Confirming removal of scholar {discordUID}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Scholar Name", value=f"{name}")
    embed.add_field(name=":id: Scholar Discord ID", value=f"{discordUID}")

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


async def updateScholarShare(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isManager(authorID):
        await handleResponse(message,"You must be a manager to use this command",isSlash)
        return            
    
    if len(args) < 3:
        await handleResponse(message,"Please specify: discordUID scholarShare",isSlash)
        return

    if not args[1].isnumeric() or not isFloat(args[2]):
        await handleResponse(message,"Please ensure your inputs are numbers",isSlash)
        return

    discordUID = args[1]
    scholarShare = round(float(args[2]),3)
    name = await getNameFromDiscordID(discordUID)

    if scholarShare < 0.01 or scholarShare > 1.0:
        await handleResponse(message,"Please ensure your scholar share is between 0.01 and 1.00",isSlash)
        return

    res = await DB.getDiscordID(discordUID)
    user = res["rows"]
    if user is None or (user is not None and int(user["is_scholar"]) == 0):
        await handleResponse(message,"Did not find a scholar with this discord ID",isSlash)
        return

    oldShare = float(user["share"])
    change = float(scholarShare) - oldShare
    
    if change == 0.0:
        await handleResponse(message,"This is not a change, please specify a new share",isSlash)
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
    embed.add_field(name="Old Share", value=f"{round(oldShare*100,2)}%")
    embed.add_field(name="New Share", value=f"{round(scholarShare*100,2)}%")
    
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


async def updateScholarAddress(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    
    if len(args) < 2:
        await handleResponse(message,"Please specify: payoutAddress",isSlash)
        return

    if len(args) > 2 and args[2].isnumeric() and isManager:
        discordId = int(args[2])

    payoutAddr = args[1]
    name = await getNameFromDiscordID(discordId)

    if not payoutAddr.startswith("ronin:") and not payoutAddr.startswith("0x"):
        await handleResponse(message,"Please ensure the payout address starts with ronin: or 0x",isSlash)
        return

    res = await DB.getDiscordID(discordId)
    user = res["rows"]
    if user is None or (user is not None and (user["is_scholar"] is None or int(user["is_scholar"]) == 0)):
        await handleResponse(message,"Did not find a scholar with this discord ID",isSlash)
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


async def addManager(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isOwner(authorID):
        await handleResponse(message,"You must be the owner to use this command",isSlash)
        return
    
    if len(args) < 2:
        await handleResponse(message,"Please specify: discordUID",isSlash)
        return

    discordUID = args[1]
    name = await getNameFromDiscordID(discordUID)
    
    # confirm with react
    embed = discord.Embed(title="Add Manager Confirmation", description=f"Confirming adding Manager {discordUID}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Manager Name", value=f"{name}")
    embed.add_field(name=":id: Manager Discord ID", value=f"{discordUID}")

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
    
    res = await DB.addManager(discordUID, name)
    await confMsg.reply(content=f"<@{authorID}>: " + res['msg'])


async def removeManager(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    if not await DB.isOwner(authorID):
        await handleResponse(message,"You must be the owner to use this command",isSlash)
        return            

    if len(args) < 2:
        await handleResponse(message,"Please specify: discordUID",isSlash)
        return            

    discordUID = args[1]
    name = await getNameFromDiscordID(discordUID)

    # confirm with react
    embed = discord.Embed(title="Remove Manager Confirmation", description=f"Confirming removing Manager {discordUID}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name=":book: Manager Name", value=f"{name}")
    embed.add_field(name=":id: Manager Discord ID", value=f"{discordUID}")

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


async def membershipCommand(message, args, isManager, discordId, guildId, isSlash=False):
    res = await DB.getMembershipReport()
    name = await getNameFromDiscordID(ownerID)    

    embed = discord.Embed(title="Program Membership Report", description=f"Membership report for {programName}",
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


def getLoadingContent(complete, total):
    unixtime = int(time.time())
    disptime = str(datetime.datetime.fromtimestamp(unixtime).strftime("%H:%M:%S"))
    msg = 'Mass Payout Progress\n'
    msg += '\n['
    percent = (float(complete) / float(total))*100.0
    for i in range(1,11):
        if i*10 <= percent < (i + 1)*10:
            msg += ':rocket:'
        elif percent > i*10:
            msg += ':cloud:'
        else:
            msg += ':black_large_square:'
    msg += ':full_moon:] ({:.2f}%, {}/{})'.format(percent, complete, total)
    return msg


async def payoutCommand(message, args, isManager, discordId, guildId, isSlash=False):
    authorID = message.author.id
    
    mp = await DB.getProperty("massPay")
    if not mp["success"]:
        await handleResponse(message,"Failed to query database for massPay property",isSlash)
        return
    if mp["rows"] is not None and (mp["rows"]["realVal"] is None or int(mp["rows"]["realVal"]) != 0):
        await handleResponse(message,"Individual payouts are disabled. Ask your manager to run a mass payout or to enable individual payouts.",isSlash)
        return

    res = await DB.getDiscordID(discordId)
    user = res["rows"]
    if user is None or (user is not None and (user["is_scholar"] is None or int(user["is_scholar"]) == 0)):
        await handleResponse(message,"Did not find a scholar with your discord ID",isSlash)
        return

    res = await DB.getProperty("devDonation")
    if not res["success"]:
        await handleResponse(message,"Failed to query database for devDonation property",isSlash)
        return
    
    devDonation = 0.0
    if res["rows"]["realVal"] is not None:
        devDonation = round(float(res["rows"]["realVal"]),3)
    
    name = user['name']
    payoutAddr = user['payout_addr']
    share = float(user['share'])
    seedNum = user['seed_num']
    accountNum = user['account_num']

    if payoutAddr is None or payoutAddr == "":
        await handleResponse(message,"Please set your payout address with '&setPayoutAddress ronin:...' first",isSlash)
        return

    # confirm with react
    embed = discord.Embed(title="Individual Scholar Payout Confirmation", description=f"Confirming payout for {name}",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name="Scholar Name", value=f"{name}")
    embed.add_field(name="Scholar Discord ID", value=f"{discordId}")
    embed.add_field(name="Scholar Share", value=f"{round(share*100,3)}")
    embed.add_field(name="Payout Address", value=f"{payoutAddr}")
    embed.add_field(name="Note", value="Please carefully check the payout address! Misplaced SLP cannot be recovered!")

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
    
    scholarSS = ScholarsDict[str(discordId)]
    key = scholarSS[2]        # discordID's privateKey
    address = scholarSS[1]    # discordID's address

    try:
        #devSlp, ownerSlp, scholarSlp = ClaimSLP.slpClaiming(key, address, payoutAddr, ownerRonin, share, devDonation)
        claimRes = await ClaimSLP.slpClaiming(key, address, payoutAddr, ownerRonin, share, devDonation)
    except Exception as e:
        logger.error(e)
        await processMsg.reply(content=f"<@{discordId}> there was an error while processing your payout. Please work with your manager to have it manually resolved.")
        return

    if claimRes is False:
        await processMsg.reply(content=f"<@{authorID}>: Your account is not available to claim yet")
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

    roninTx = "https://explorer.roninchain.com/tx/"
    roninAddr = "https://explorer.roninchain.com/address/"
    embed2 = discord.Embed(title="Individual Scholar Payout Results", description=f"Data regarding the payout",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed2.add_field(name="SLP Paid to Scholar", value=f"[{scholarAmt}]({roninTx}{scholarTx})")
    if devTx is not None:
        embed2.add_field(name="SLP Donated to Devs", value=f"[{devAmt}]({roninTx}{devTx})")
    embed2.add_field(name="SLP Paid to Manager", value=f"[{ownerAmt}]({roninTx}{ownerTx})")
    embed2.add_field(name="Total SLP Farmed", value=f"[{totalAmt}]({roninTx}{claimTx})")
    embed.add_field(name="Scholar Share Paid To", value=f"[{payoutAddr}]({roninAddr}{payoutAddr})")
    
    await processMsg.reply(content=f"<@{authorID}>", embed=embed2)


async def payoutAllScholars(message, args, isManager, discordId, guildId, isSlash=False): 
    authorID = message.author.id
    if not await DB.isManager(authorID):
        await handleResponse(message,"You must be a manager to use this command",isSlash)
        return

    scholarsDB = await DB.getAllScholars()
    if not scholarsDB["success"]:
        await handleResponse(message,"Failed to query database for scholars",isSlash)
        return
    scholarCount = len(scholarsDB['rows'])

    res = await DB.getProperty("devDonation")
    if not res["success"]:
        await handleResponse(message,"Failed to query database for devDonation property",isSlash)
        return
    
    devDonation = 0.0
    if res["rows"]["realVal"] is not None:
        devDonation = round(float(res["rows"]["realVal"]),3)
    
    # confirm with react
    embed = discord.Embed(title="All Scholar Payout Confirmation", description=f"Confirming paying out all scholars",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name="Scholar Count", value=f"{scholarCount}")

    mp = await DB.getProperty("massPay")
    if not mp["success"]:
        await handleResponse(message,"Failed to query database for massPay property",isSlash)
        return
    if mp["rows"] is not None and (mp["rows"]["realVal"] is None or int(mp["rows"]["realVal"]) == 0):
        embed.add_field(name="Note", value="Running a mass payment will disable individual payments. You will have to re-enable them later with '&setProperty massPay 0'")

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

    skipped = 0
    processed = 0
    errors = 0
    devTotal = 0
    ownerTotal = 0
    scholarTotal = 0
    for row in scholarsDB["rows"]:
        scholarID = row['discord_id']
        
        scholarSS = ScholarsDict[str(scholarID)]
        key = scholarSS[2]        # discordID's privateKey
        address = scholarSS[1]    # discordID's address

        scholarAddress = row['payout_addr']
        scholarShare = round(float(row['share']),3)

        if scholarAddress is None or scholarAddress == "":
            skipped += 1
            msg = getLoadingContent(processed+skipped, scholarCount)
            await loadMsg.edit(content=msg)
            continue

        devSlp = 0
        ownerSlp = 0
        scholarSlp = 0
        res = None
        try:
            res = await ClaimSLP.slpClaiming(key, address, scholarAddress, ownerRonin, scholarShare, devDonation)
        except Exception as e:
            logger.error(e)
            errors += 1

        if res is not False and res is not None:
            processed += 1
        else:
            skipped += 1
            msg = getLoadingContent(processed+skipped, scholarCount)
            await loadMsg.edit(content=msg)
            continue

        if res["devAmount"] is not None:
            devTotal += res["devAmount"]
        ownerTotal += res["ownerAmount"]
        scholarTotal += res["scholarAmount"]

        msg = getLoadingContent(processed+skipped, scholarCount)
        await loadMsg.edit(content=msg)
    msg = getLoadingContent(processed+skipped, scholarCount)
    await loadMsg.edit(content=msg)

    grandTotal = devTotal + ownerTotal + scholarTotal

    embed2 = discord.Embed(title="All Scholar Payout Results", description=f"Data regarding the mass payout",
                          timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed2.add_field(name="Scholars Paid", value=f"{processed}")
    embed2.add_field(name="Scholars Skipped/Not Ready", value=f"{skipped}")
    embed2.add_field(name="SLP Paid to Scholars", value=f"{scholarTotal}")
    embed2.add_field(name="SLP Donated to Devs", value=f"{devTotal}")
    embed2.add_field(name="SLP Paid to Manager", value=f"{ownerTotal}")
    embed2.add_field(name="Total SLP Farmed", value=f"{grandTotal}")
    
    await loadMsg.reply(content=f"<@{authorID}>", embed=embed2)


async def dailyCommand(message, args, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()     

    # check if they're a valid scholar
    if str(message.author.id) in ScholarsDict or isManager:

        # check if the request is for someone else's data
        tId = discordId
        if len(args) > 1 and len(args[1].strip()) > 0:
            for dId in ScholarsDict:
                if args[1] in ScholarsDict[dId][0]:
                    tId = dId

        scholar = ScholarsDict[str(tId)]

        roninAddr = scholar[1]
        roninKey = scholar[2]

        if roninAddr == "" or roninKey == "":
            msg = 'Sorry <@' + str(discordId) + '>, your manager has not configured game data access.'
            if isSlash:
                await message.edit(content=msg)
            else:
                await message.reply(msg)

        # fetch data
        res = await getPlayerDailies(discordId, tId, scholar[0], roninKey, roninAddr, guildId)

        if res is None:
            msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error fetching your stats. Please try again later.'
            if isSlash:
                await message.edit(content=msg)
            else:
                await message.reply(msg)
            return

        # send results
        # await message.channel.send(res["msg"])
        if isSlash:
            await message.edit(embed=res["embed"])
        else:
            await message.reply(embed=res["embed"])

    else:
        msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + programName + '\'s scholars.'
        if isSlash:
            await message.edit(content=msg)
        else:
            await message.reply(msg)

    return


async def battlesCommand(message, args, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()     

    if len(args) > 1 and (args[1].startswith("0x") or args[1].startswith("ronin:")):
        roninAddr = args[1].replace("ronin:","0x")

        # fetch data
        res = await getRoninBattles(roninAddr)

        if res is None:
            msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error fetching the battles, or there are 0 battles to fetch. Please try again later.'
            if isSlash:
                await message.edit(content=msg)
            else:
                await message.reply(msg)
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
                await message.edit(embed=res["embed"]) #file=combinedFile
            else:
                await message.reply(file=combinedFile,embed=res["embed"])

    else:
        # check if they're a valid scholar
        if str(message.author.id) in ScholarsDict or isManager:

            # check if the request is for someone else's data
            tId = discordId
            if len(args) > 1 and len(args[1].strip()) > 0:
                for dId in ScholarsDict:
                    if args[1] in ScholarsDict[dId][0]:
                        tId = dId

            scholar = ScholarsDict[str(tId)]

            roninAddr = scholar[1]

            if roninAddr == "":
                msg = 'Sorry <@' + str(discordId) + '>, your manager has not configured game data access.'
                if isSlash:
                    await message.edit(content=msg)
                else:
                    await message.reply(msg)
                return

            # fetch data
            res = await getScholarBattles(discordId, tId, scholar[0], roninAddr)

            if res is None:
                msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error fetching your battles, or there are 0 battles to fetch. Please try again later.' 
                if isSlash:
                    await message.edit(content=msg)
                else:
                    await message.reply(msg)
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
                    await message.edit(embed=res["embed"]) #file=combinedFile
                else:
                    await message.reply(file=combinedFile,embed=res["embed"])
        else:
            msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + programName + '\'s scholars.'
            if isSlash:
                await message.edit(content=msg)
            else:
                await message.reply(msg)

        return


async def axiesCommand(message, args, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()     

    # check if user is a valid scholar
    if str(message.author.id) in ScholarsDict or isManager:

        # check if request is for another user's data
        tId = str(discordId)
        if len(args) > 1 and len(args[1].strip()) > 0:
            for dId in ScholarsDict:
                if args[1] in ScholarsDict[dId][0]:
                    tId = str(dId)

        ind = -1
        if len(args) > 2 and args[2].isnumeric():
            ind = int(args[2])

        mobile = 0
        if len(args) > 3 and (args[3] == "1" or args[3].lower() == "m"):
            mobile = 1

        scholar = ScholarsDict[str(tId)]

        roninAddr = scholar[1]
        roninKey = scholar[2]

        # fetch axie data
        res = await getPlayerAxies(tId, scholar[0], roninKey, roninAddr, ind)

        if res is None:
            msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error fetching your axies. Please try again later.'
            if isSlash:
                await message.edit(content=msg)
            else:
                await message.reply(msg)
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
                await message.edit(embed=embed) #file=combinedFile
            else:
                await message.reply(file=combinedFile,embed=embed)

    else:
        msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + programName + '\'s scholars.'
        if isSlash:
            await message.edit(content=msg)
        else:
            await message.reply(msg)

    return


async def summaryCommand(message, args, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()     

    # check for sorting instructions
    sort = "avgSlp"
    asc = False
    ascText = "desc"
    if len(args) > 1 and args[1].lower() in ["claim", "avgslp", "slp", "mmr", "adventure", "adv", "arena", "rank",
                                             "battle"]:
        sort = args[1].lower()
    if len(args) > 2 and args[2].lower() in ["asc", "desc"]:
        if args[2].lower() == "asc":
            asc = True
            ascText = "asc"

    # fetch the data
    table, cacheExp = await getScholarSummary(ScholarsDict, sort.lower(), asc, guildId)

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
    
    fig = go.Figure(data=[go.Table(
        columnwidth = [75,400,100,200,150,200,150,150,150,150,100,200],
        header=dict(values=list(table.columns),
            fill_color="paleturquoise",
            align='center'),
        cells=dict(values=table.T.values,
            fill_color='lavender',
            align='center'))
    ])
    fig.update_layout(margin=dict(
        l=0, #left margin
        r=0, #right margin
        b=0, #bottom margin
        t=0  #top margin
    ))
    fName = 'images/summary' + str(int(time.time())) + '.png'
    fig.write_image(fName, width=1200, height=20*len(table)+30)

    if isSlash:
        await message.edit(content=msg)
        await message.followup(file=discord.File(fName))
    else:
        await message.reply(content=msg,file=discord.File(fName))

    os.remove(fName)


async def exportCommand(message, isManager, isSlash=False):
    if not isManager:
        message.reply("Sorry, this command is only for managers!")
        return

    df = await getScholarExport(ScholarsDict)
    df.to_csv("export.csv", index=False)

    if isSlash:
        await message.channel.send(file=discord.File('export.csv'))
    else:
        await message.reply(file=discord.File('export.csv'))
    os.remove("export.csv")


async def topCommand(message, args, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()     

    # check for sorting instructions
    sort = "mmr"
    asc = False
    ascText = "desc"
    if len(args) > 1 and args[1].lower() in ["avgslp", "slp", "mmr", "adventure", "adv", "arena", "rank", "battle"]:
        sort = args[1].lower()

    # fetch the data
    table, cacheExp = await getScholarTop10(ScholarsDict, sort.lower())

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
    
    fig = go.Figure(data=[go.Table(
        columnwidth = [75,400,100,200,150,200,150,150,150,150,100,200],
        header=dict(values=list(table.columns),
            fill_color="paleturquoise",
            align='center'),
        cells=dict(values=table.T.values,
            fill_color='lavender',
            align='center'))
    ])
    fig.update_layout(margin=dict(
        l=0, #left margin
        r=0, #right margin
        b=0, #bottom margin
        t=0  #top margin
    ))
    fName = 'images/top' + str(int(time.time())) + '.png'
    fig.write_image(fName, width=1200, height=20*len(table)+30)

    if isSlash:
        await message.edit(content=msg)
        await message.followup(file=discord.File(fName))
    else:
        await message.reply(content=msg,file=discord.File(fName))

    os.remove(fName)


async def alertsCommand(message, args, isSlash=False):
    global forceAlert
    global alertPing
    
    if not isSlash:
        await message.channel.trigger_typing()     

    ping = False
    if len(args) > 1 and args[1] == "1":
        ping = True

    alertPing = ping
    forceAlert = True

    logger.info(f"Processing on-demand alert, ping={alertPing},force={forceAlert}")

    if isSlash:
        await message.edit(content="Processing!")
    else:
        await message.reply("Processing!")

