# Author: Michael Conard
# Purpose: An Axie Infinity utility bot. Gives QR codes and daily progress/alerts.

import discord
import os
import traceback
import math
import configparser
import json
import datetime
import matplotlib.pyplot as plt
import pandas as pd
from pandas.plotting import table as tableTool
import plotly.graph_objects as go

from discord.ext import tasks, commands
from dislash import slash_commands
from dislash.interactions import *
from loguru import logger

from SecretStorage import *
from Common import *
from UtilBot import *
import Commands
from Slash import *
import DB

# Event Listeners

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(prefix + 'qr to get QR code!'))
    print('\nWe are logged in as {0.user}'.format(client))

    await DB.createMainTables()

    for guild in client.guilds:
        found = False
        for emoji in guild.emojis:
            if emoji.name == "slp":
                found = True
                slpEmojiID[guild.id] = emoji.id
        if found == False:
            slpEmojiID[guild.id] = None


@client.event
# Listen for an incomming message
async def on_message(message):
    global forceAlert
    global alertPing

    # check if the message fits our prefix
    if not message.content.startswith(prefix):
        return

    # set important IDs
    discordId = message.author.id
    channelId = message.channel.id
    guildId = None
    if message.guild == None:
        # command was DMed to the bot
        guildId = None
    else:
        # command was in a server channel
        guildId = message.guild.id

    # If the author is the robot itself, then do nothing!
    if message.author == client.user:
        return

    isManager = False
    managerIds = await DB.getAllManagerIDs()
    logger.info("Manager IDs")
    logger.info(managerIds)
    if int(discordId) in managerIds:
        isManager = True

    args = message.content.split(" ")

    # If the user requests a QR code
    if message.content == prefix + "qr":
        await Commands.qrCommand(message, isManager, discordId, guildId)
        return   
    
    # user requests daily progress
    elif args[0] == prefix + "daily":
        await Commands.dailyCommand(message, args, isManager, discordId, guildId)
        return

    # user requests recent battles
    elif args[0] == prefix + "battles":
        await Commands.battlesCommand(message, args, isManager, discordId, guildId)
        return

    # user requests axie data
    elif args[0] == prefix + "axies":
        await Commands.axiesCommand(message, args, isManager, discordId, guildId)
        return

    # user requests scholar summary data, can be restricted to manager only via the comment
    elif args[0] == prefix + "summary":  # and isManager:
        await Commands.summaryCommand(message, args, isManager, discordId, guildId)
        return

    # user requests scholar top10 data, can be restricted to manager only via the comment
    elif args[0] == prefix + "top":  # and isManager:
        await Commands.topCommand(message, args, isManager, discordId, guildId)
        return

    # user requests alerts, must be manager
    elif args[0] == prefix + "alert" and isManager:
        await Commands.alertsCommand(message, args)
        return
    
    # get export csv of scholars
    elif args[0] == prefix + "export" and isManager:
        await Commands.exportCommand(message, isManager)
        return

    elif args[0] == prefix + "getProperty":
        await Commands.getPropertyCommand(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "setProperty" and isManager:
        await Commands.setPropertyCommand(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "getScholar":
        await Commands.getScholar(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "addScholar" and isManager:
        await Commands.addScholar(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "removeScholar" and isManager:
        await Commands.removeScholar(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "updateScholarShare" and isManager:
        await Commands.updateScholarShare(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "setPayoutAddress":
        await Commands.updateScholarAddress(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "addManager" and isManager:
        await Commands.addManager(message, args, isManager, discordId, guildId)
        return

    elif args[0] == prefix + "removeManager" and isManager:
        await Commands.removeManager(message, args, isManager, discordId, guildId)
        return
    
    elif args[0] == prefix + "membership":
        await Commands.membershipCommand(message, args, isManager, discordId, guildId)
        return
     
    elif args[0] == prefix + "payout":
        await Commands.payoutCommand(message, args, isManager, discordId, guildId)
        return
    
    elif args[0] == prefix + "massPayout" and isManager:
        await Commands.payoutAllScholars(message, args, isManager, discordId, guildId)
        return

    # user asked for command help
    elif message.content == prefix + "help":
        await helpCommand(message, discordId)
        return

    logger.warning('Unknown command entered: {}'.format(message.content))
    return


# Cron Jobs

# task to send alerts at scheduled intervals regarding scholar progress
@tasks.loop(seconds=60.0)
async def checkEnergyQuest():
    global alertPing
    global forceAlert

    await client.wait_until_ready()

    try:
        rn = datetime.datetime.now(timezone.utc)

        ping = alertPing
        logger.info(f"Checking for time based tasks ping={alertPing}, force={forceAlert}; {rn}")

        # check if it's time to run a task
        if forceAlert or (rn.hour == 23 and rn.minute == 0):  # allow 7pm EST / 11pm UTC
            # energy / quest alerts
            logger.info("Processing near-reset alerts")

            channel = client.get_channel(alertChannelId);
            msg = ""

            if not forceAlert:
                msg = "Hello %s! The %s daily reset is in 1 hour.\n\n" % (programName, str(rn.date()))
            else:
                msg = "Hello %s!\n\n" % (programName)

            forceAlert = False
            count = 0

            greenCheck = ":white_check_mark:"
            redX = ":x:"

            # for each scholar
            for dId in ScholarsDict:
                scholar = ScholarsDict[dId]

                name = scholar[0]
                roninAddr = scholar[1]
                roninKey = scholar[2]

                # fetch daily progress data
                res = await getPlayerDailies("", dId, scholar[0], roninKey, roninAddr)

                # configure alert messages
                if res is not None:
                    alert = res["questSlp"] != 25 or res["energy"] > 0 or res["pveSlp"] < 50 or res["mmr"] < 1000
                    congrats = res["pvpCount"] >= 15
                    if alert or congrats:
                        # send early to avoid message size limits
                        if len(msg) >= 1600:
                            await channel.send(msg)
                            msg = ""

                        if ping:
                            msg += '<@' + str(dId) + '>:\n'
                        else:
                            msg += name.replace('`', '') + ":\n"

                        if res["questSlp"] != 25:
                            msg += '%s You have not completed/claimed the daily quest yet\n' % (redX)
                        if res["energy"] > 0:
                            msg += '%s You have %d energy remaining\n' % (redX, res["energy"])
                        if res["pveSlp"] < 50:
                            msg += '%s You only have %d/50 Adventure SLP completed\n' % (redX, res["pveSlp"])
                        if res["mmr"] < 1000:
                            msg += '%s You are only at %d MMR in Arena. <800 = no SLP.\n' % (redX, res["mmr"])
                        if res["pvpCount"] >= 15:
                            msg += '%s Congrats on your %d Arena wins! Wow!\n' % (greenCheck, res["pvpCount"])
                    if alert:
                        count += 1

            if count == 0:
                msg += '\n'
                msg += "Woohoo! It seems everyone has used their energy and completed the quest today!"

            # send alerts
            alertPing = True
            await channel.send(msg)

        if leaderboardPeriod < 25 and rn.hour % leaderboardPeriod == 0 and rn.minute == 0:  # allow periodically
            logger.info("Processing scheduled leaderboard posting")

            channel = client.get_channel(leaderboardChannelId);
            
            # fetch the data
            sort = "mmr"
            ascText = "desc"
            table, cacheExp = await getScholarSummary(ScholarsDict, sort, False)

            # error
            if table is None or cacheExp is None:
                logger.error("Failed to build scheduled leaderboard post")
            
            else:
                # send results
                msg = 'Hello ' + programName + ', here is the scholar summary sorted by `' + sort + " " + ascText + "`:"

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

                await channel.send(content=msg,file=discord.File(fName))

                os.remove(fName)
            pass

    except Exception as e:
        logger.error("Error in checkEnergyQuest")
        logger.error(e)
        #traceback.print_exc()

        await sendErrorToManagers(e, "cron job")
    
    pass


# Run tasks
checkEnergyQuest.start()

# Run the client
client.run(DiscordBotToken)

