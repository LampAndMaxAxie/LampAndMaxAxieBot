# Author: Michael Conard
# Purpose: An Axie Infinity utility bot. Gives QR codes and daily progress/alerts.

import discord
import os
import traceback
import math
import configparser
import json
import datetime

from discord.ext import tasks, commands

from SecretStorage import *
from Common import *
from UtilBot import *

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
    msg += ' - `' + prefix + 'top [category]`: returns the top 10 scholars, avgslp/slp/adv for SLP or mmr/rank/arena for Arena\n'

    if isSlash:
        await message.edit(content=msg)
    else:
        await message.reply(msg)
    return


async def qrCommand(message, isManager, discordId, guildId, isSlash=False):
    if not isSlash:
        await message.channel.trigger_typing()     
    
    if os.path.exists("./qr/" + str(message.author.id)+"QRCode.png"):
        os.remove("./qr/" + str(message.author.id)+"QRCode.png")

    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    print('\n')

    # check for user's Discord ID
    if message.author.id in qrBlacklist:
        msg = "Sorry, but QR generation isn't working for your account right now. Please talk to your manager."
        message.author.send(msg)

        if guildId is not None:
            msg = 'Hi <@' + str(discordId) + '>, please check your DMs!'
            if isSlash:
                await message.edit(content=msg)
            else:
                await message.reply(msg)

        return

    if str(message.author.id) in ScholarsDict:
        print("This user received their QR Code : " + message.author.name)

        scholar = ScholarsDict[str(message.author.id)]

        # discordID's privateKey
        accountPrivateKey = scholar[2]
        # discordID's address
        accountAddress = scholar[1]

        if accountPrivateKey == "" or accountAddress == "":
            msg = 'Sorry <@' + str(discordId) + '>, your manager has not configured QR code generation.'
            if isSlash:
                await message.edit(content=msg)
            else:
                await message.reply(msg)
            return

        accessToken = getPlayerToken(accountPrivateKey, accountAddress)

        if accessToken == None:
            msg = 'Sorry <@' + str(discordId) + '>, there was an issue with your request. Please try again later.'
            if isSlash:
                await message.edit(content=msg)
            else:
                await message.reply(msg)
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
            if isSlash:
                await message.edit(content=msg)
            else:
                await message.reply(msg)

        return

    else:
        print("This user didn't receive a QR Code : " + message.author.name)
        msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + managerName + '\'s scholars.'
        
        if isSlash:
            await message.edit(content=msg)
        else:
            await message.reply(msg)
        return


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

        if res == None:
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
        msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + managerName + '\'s scholars.'
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

        if res == None:
            msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error fetching the battles, or there are 0 battles to fetch. Please try again later.'
            if isSlash:
                await message.edit(content=msg)
            else:
                await message.reply(msg)
            return

        # send results
        # await message.channel.send(res["msg"])
        if res['image'] == None:
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
                await message.reply('Sorry <@' + str(discordId) + '>, your manager has not configured game data access.')
                if isSlash:
                    await message.edit(content=msg)
                else:
                    await message.reply(msg)
                return

            # fetch data
            res = await getScholarBattles(discordId, tId, scholar[0], roninAddr)

            if res == None:
                msg = 'Hello <@' + str(discordId) + '>! Unfortunately, there was an error fetching your battles, or there are 0 battles to fetch. Please try again later.' 
                if isSlash:
                    await message.edit(content=msg)
                else:
                    await message.reply(msg)
                return

            # send results
            # await message.channel.send(res["msg"])
            if res['image'] == None:
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
            msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + managerName + '\'s scholars.'
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

        if res == None:
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

        if res['image'] == None:
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
        msg = 'Hello <@' + str(discordId) + '>. Unfortunately, you do not appear to be one of ' + managerName + '\'s scholars.'
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

    if len(table) <= 15:
        msg += '```\n' + table.to_string(index=False) + '```'
        msg += '\nCached until: `' + str(cacheExp) + '`'

        if isSlash:
            await message.edit(content=msg)
        else:
            await message.reply(msg)
    else:
        headersOn = False
        colWidths = [4, 20, 5, 10, 6, 8, 6, 7, 7, 6, 6, 11]
        maxWidth = 20
        for i in range(0, len(table), 15):
            if i + 15 >= len(table):
                df = table.loc[(table['Pos'] >= i)]

                msg += '```' + df.to_string(index=False, header=headersOn, col_space=colWidths,
                                            max_colwidth=maxWidth) + '```'
                msg += '\nCached until: `' + str(cacheExp) + '`'
                if isSlash:
                    await message.followup(content=msg)
                else:
                    await message.channel.send(msg)
                break
            else:
                df = table.loc[(table['Pos'] >= i) & (table['Pos'] < i + 15)]
                if i == 0:
                    msg += '```' + df.to_string(index=False, col_space=colWidths, max_colwidth=maxWidth) + '```'
                    if isSlash:
                        await message.edit(content=msg)
                    else:
                        await message.reply(msg)
                else:
                    msg += '```' + df.to_string(index=False, header=headersOn, col_space=colWidths,
                                                max_colwidth=maxWidth) + '```'
                    if isSlash:
                        await message.followup(content=msg)
                    else:
                        await message.channel.send(msg)
                msg = ""
    pass


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
    msg = 'Hello <@' + str(discordId) + '>, here is the scholar top 10 filtered by `' + sort + "`:"

    msg += '```\n' + table.to_string(index=False) + '```'
    msg += '\nCached until: `' + str(cacheExp) + '`'

    if isSlash:
        await message.edit(content=msg)
    else:
        await message.reply(msg)


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

    print("Processing on-demand alert")

    if isSlash:
        await message.edit(content="Processing!")
    else:
        await message.reply("Processing!")

