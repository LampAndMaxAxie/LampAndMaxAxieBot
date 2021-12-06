import binascii
import configparser
import getpass
import json
import os

import discord
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util import Counter
from discord.ext import commands
from dislash import slash_commands
from dislash.interactions import *
from eth_account import Account
from loguru import logger
from web3 import Web3

import SeedStorage

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
    ownerRonin = config.get('Manager', 'ownerRoninAddr').replace("ronin:","0x")
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
    payBlacklist = json.loads(config.get('Bot', 'payBlacklistIds'))
    prefix = config.get('Bot', 'prefix')

    dmPayoutsToScholars = config.get('Bot', 'dmPayoutsToScholars')
    if dmPayoutsToScholars == "True":
        dmPayoutsToScholars = True
    else:
        dmPayoutsToScholars = False
    
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
    logger.error("Please fill out a [Bot] section with qrBlacklistIds, prefix, dmErrorsToManagers, dmPayoutsToScholars, and hideScholarRonins.")
    exit()

# Setup Discord Bot
intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix=prefix, intents=intents)
slash = slash_commands.SlashClient(client)

# Globals
decryptionPass = ""
decryptionKey = ""
mnemonicList = SeedStorage.SeedList
Account.enable_unaudited_hdwallet_features()

# 32 bit keys => AES256 encryption
key_bytes = 32

if not os.path.exists("./iv.dat"):
    print("IV data file not found. Please restore the file or re-run your seed encryption.")
    exit()

if os.path.exists("./.botpass"):
    with open("./.botpass", "r") as f:
        logger.info("Using password saved in .botpass file")
        decryptionPass = f.read().strip()
        decryptionKey = PBKDF2(decryptionPass, "axiesalt", key_bytes)
else:
    print("Note, the password field is hidden so it will not display what you type.")
    decryptionPass = getpass.getpass().strip()
    decryptionKey = PBKDF2(decryptionPass, "axiesalt", key_bytes)

iv = None
with open("iv.dat", "rb") as f:
    try:
        iv = f.read()
    except:
        logger.error("There was an error reading your IV data file.")
        exit()


# Functions
# Encryption methodology adopted from https://stackoverflow.com/a/44662262
# 32 bit key, binary plaintext string to encrypt, and IV binary string
def encrypt(key, plaintext, iv=None):
    assert len(key) == key_bytes

    # create random IV if one not provided
    if iv is None:
        iv = Random.new().read(AES.block_size)

    # convert IV to integer
    iv_int = int(binascii.hexlify(iv), 16)

    # create counter using the IV
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)

    # create cipher object
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    # encrypt the string and return the IV/ciphertext
    ciphertext = aes.encrypt(plaintext)
    return iv, ciphertext


# 32 bit key, IV binary string, and ciphertext to decrypt
def decrypt(key, iv, ciphertext):
    assert len(key) == key_bytes

    # convert IV to integer and create counter using the IV
    iv_int = int(binascii.hexlify(iv), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)

    # create cipher object
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    # decrypt ciphertext and return the decrypted binary string
    plaintext = aes.decrypt(ciphertext)
    return plaintext


async def messageManagers(msg, managerIds):
    global client
    global dmErrorsToManagers

    if not dmErrorsToManagers:
        return

    for managerId in managerIds:
        logger.warning("Message error to " + str(managerId))
        user = await client.fetch_user(int(managerId))

        if user is not None:
            await user.send(msg)
        else:
            logger.error("Failed to DM manager: " + str(managerId))


async def getNameFromDiscordID(UID):
    logger.info(f"Fetching name for {UID}")
    usr = await client.fetch_user(int(UID))
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


async def getFromMnemonic(seedNumber, accountNumber, scholarAddress):
    try:
        mnemonic = decrypt(decryptionKey, iv, mnemonicList[int(seedNumber) - 1]).decode("utf8")
        scholarAccount = Account.from_mnemonic(mnemonic, "", "m/44'/60'/0'/0/" + str(int(accountNumber) - 1))
        if scholarAddress.lower() == scholarAccount.address.lower():
            #logger.info("Got the key for " + scholarAddress + " correctly")
            return {
                "key": Web3.toHex(scholarAccount.key),
                "address": scholarAccount.address.lower()
            }
        else:
            logger.error("Account Address did not match derived address")
            logger.error(f"{scholarAddress} != {scholarAccount.address}")
            return None
    except Exception:
        logger.error("Exception in getFromMnemonic, not logging trace since key or passwords may be involved")
        # logger.error(traceback.format_exc())
        return None


# check password
try:
    x = decrypt(decryptionKey, iv, mnemonicList[0]).decode("utf8")
except:
    print(f"Password failed.")
    exit()
