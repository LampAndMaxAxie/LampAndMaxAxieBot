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
from dislash import slash_commands
from dislash.interactions import *

from SecretStorage import *
from Common import *
from UtilBot import *
from Commands import *
from Slash import *


# Event Listeners

@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(prefix + 'qr to get QR code!'))
    print('\nWe are logged in as {0.user}'.format(client))

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
    if discordId in managerIds:
        isManager = True

    args = message.content.split(" ")

    # If the user requests a QR code
    if message.content == prefix + "qr":
        await qrCommand(message, isManager, discordId, guildId)
        return   
    
    # user requests daily progress
    elif args[0] == prefix + "daily":
        await dailyCommand(message, args, isManager, discordId, guildId)
        return

    # user requests daily progress
    elif args[0] == prefix + "battles":
        await battlesCommand(message, args, isManager, discordId, guildId)
        return

    # user requests axie data
    elif args[0] == prefix + "axies":
        await axiesCommand(message, args, isManager, discordId, guildId)
        return

    # user requests scholar summary data, can be restricted to manager only via the comment
    elif args[0] == prefix + "summary":  # and isManager:
        await summaryCommand(message, args, isManager, discordId, guildId)
        return

    # user requests scholar top10 data, can be restricted to manager only via the comment
    elif args[0] == prefix + "top":  # and isManager:
        await topCommand(message, args, isManager, discordId, guildId)
        return

    # user requests alerts, must be manager
    elif args[0] == prefix + "alert" and isManager:
        await alertsCommand(message, args)
        return

    # user asked for command help
    elif message.content == prefix + "help":
        await helpCommand(message, discordId)
        return

    print('Unknown command entered: {}'.format(message.content))
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

        # check if it's time to run a task
        if forceAlert or (rn.hour == 23 and rn.minute == 0):  # allow 7pm EST / 11pm UTC
            # energy / quest alerts
            print("Processing near-reset alerts")

            channel = client.get_channel(channelId);
            msg = ""

            if not forceAlert:
                msg = "Hello %s\'s Scholars! The %s daily reset is in 1 hour.\n\n" % (managerName, str(rn.date()))
            else:
                msg = "Hello %s\'s Scholars!\n\n" % (managerName)

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
                    alert = res["questSlp"] != 25 or res["energy"] > 0 or res["pveSlp"] < 50
                    congrats = res["pvpCount"] >= 15
                    if alert or congrats:
                        # send early to avoid message size limits
                        if len(msg) >= 1900:
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
                        if res["pvpCount"] >= 15:
                            msg += '%s Congrats on your %d Arena wins! Wow!\n' % (greenCheck, res["pvpCount"])
                    if alert:
                        count += 1

            if count == 0:
                msg += "Woohoo! It seems everyone has used their energy and completed the quest today!"

            # send alerts
            alertPing = True
            await channel.send(msg)

        if rn.hour == 23 and rn.minute == 58:  # allow 7:58pm EST / 11:58pm UTC
            # print("Processing SLP data near reset")
            pass

    except Exception as e:
        print("Error in checkEnergyQuest")
        traceback.print_exc()

        await sendErrorToManagers(e, "cron job")
    
    pass


# Run tasks
checkEnergyQuest.start()

# Run the client
client.run(DiscordBotToken)

