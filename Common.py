import discord
import configparser
import os
import json

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
    print("Please fill out a config.cfg file according to specifications.")
    exit()

try:
    managerName = config.get('Manager', 'managerName')
    managerIds = json.loads(config.get('Manager', 'managerIds'))
except:
    print("Please fill out a [Manager] section for managerName and managerIds.")
    exit()

try:
    channelId = int(config.get('Server', 'alertsChannelId'))
    serverIds = json.loads(config.get('Server', 'serverIds'))
except:
    print("Please fill out a [Server] section with alertsChannelId and serverId.")
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
    print("Please fill out a [Bot] section with qrBlacklistIds, prefix, dmErrorsToManagers, and hideScholarRonins.")
    exit()


# Globals
alertPing = True
forceAlert = False


# Functions
async def messageManagers(msg):
    global managerIds
    global client
    global dmErrorsToManagers

    if not dmErrorsToManagers:
        return

    for managerId in managerIds:
        print("Message error to " + str(managerId))
        user = client.get_user(int(managerId))

        if user is not None:
            await user.send(msg)
        else:
            print("Failed to DM manager: " + str(managerId))


# Setup Filesystem
if not os.path.exists("./qr/"):
    os.mkdir("qr")
if not os.path.exists("./images/"):
    os.mkdir("images")

