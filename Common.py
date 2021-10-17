import discord
import configparser
import os
import json

from loguru import logger
from discord.ext import tasks, commands
from dislash import slash_commands
from dislash.interactions import *

# Setup Discord Bot
intents = discord.Intents.default()
intents.members = True
client = commands.Bot("", intents=intents)
slash = slash_commands.SlashClient(client)


# Setup Config Parser
config = configparser.ConfigParser()
try:
    config.read(r'./config.cfg')
except:
    logger.error("Please fill out a config.cfg file according to specifications.")
    exit()

try:
    programName = config.get('Manager', 'programName')
    ownerID = config.get('Manager', 'ownerDiscordID')
    ownerRonin = config.get('Manager', 'ownerRoninAddr')
except:
    logger.error("Please fill out a [Manager] section for programName and ownerId.")
    exit()

try:
    alertChannelId = int(config.get('Server', 'alertsChannelId'))
    leaderboardChannelId = int(config.get('Server', 'leaderboardsChannelId'))
    leaderboardPeriod = int(config.get('Server', 'leaderboardsPeriodHours'))
    serverIds = json.loads(config.get('Server', 'serverIds'))
except:
    logger.error("Please fill out a [Server] section with alertsChannelId and serverIds.")
    exit()

try:
    qrBlacklist = json.loads(config.get('Bot', 'qrBlacklistIds'))
    prefix = config.get('Bot', 'prefix')
    hideScholarRonins = config.get('Bot', 'hideScholarRonins')
    if hideScholarRonins == "True":
        hideScholarRonins = True
    else:
        hideScholarRonins = False
    dmErrorsToManagers = config.get('Bot', 'dmErrorsToManagers')
    if dmErrorsToManagers == "False":
        dmErrorsToManagers = False
    else:
        dmErrorsToManagers = True
except:
    logger.error("Please fill out a [Bot] section with qrBlacklistIds, prefix, dmErrorsToManagers, and hideScholarRonins.")
    exit()


# Globals
alertPing = True
forceAlert = False


# Functions
async def messageManagers(msg, managerIds):
    global client
    global dmErrorsToManagers

    if not dmErrorsToManagers:
        return

    for managerId in managerIds:
        logger.warn("Message error to " + str(managerId))
        user = await client.fetch_user(int(managerId))

        if user is not None:
            await user.send(msg)
        else:
            logger.error("Failed to DM manager: " + str(managerId))

async def getNameFromDiscordID(id):
    logger.info(f"Fetching name for {id}") 
    usr = await client.fetch_user(int(id))
    logger.info(usr)
    if usr is None:
        return None
    return usr.name + "#" + usr.discriminator

async def handleResponse(message, content, isSlash):
    if isSlash:
        await message.edit(content=content)
    else:
        await message.reply(content=content)

def isFloat(val):
    try:
        float(val)
    except ValueError:
        return False
    return True

# Setup Filesystem
if not os.path.exists("./qr/"):
    os.mkdir("qr")
if not os.path.exists("./images/"):
    os.mkdir("images")

