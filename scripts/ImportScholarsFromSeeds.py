import sys
import DB
from Common import client, getNameFromDiscordID
import binascii
import getpass
import os
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util import Counter
from eth_account import Account
from loguru import logger
import SeedStorage

fName = "import.txt"

# Globals
mnemonicList = SeedStorage.SeedList
accounts = {}
currentCount = 0
Account.enable_unaudited_hdwallet_features()

if os.path.exists("./.botpass"):
    with open("./.botpass", "r") as f:
        logger.info("Using password saved in .botpass file")
        decryptionPass = f.read().strip()
        decryptionKey = PBKDF2(decryptionPass, "axiesalt", 32)
else:
    print("Note, the password field is hidden so it will not display what you type.")
    decryptionPass = getpass.getpass().strip()
    decryptionKey = PBKDF2(decryptionPass, "axiesalt", 32)

with open("iv.dat", "rb") as f:
    try:
        iv = f.read()
    except:
        logger.error("There was an error reading your IV data file.")
        exit()

if len(sys.argv) > 1:
    fName = str(sys.argv[1])

if not os.path.exists(fName):
    print(f"File {fName} not found, please provide the import file")
    exit()


@client.event
async def on_ready():
    await importScholars(fName)


async def importScholars(fName):
    try:
        await DB.createMainTables()
    except:
        logger.error("Failed to create tables")
        exit()
    try:
        currentCount = await getFromMnemonic()
    except:
        logger.error("Something went wrong")
        exit()
    count = 0
    with open(fName) as f:
        for line in f:
            # skip comment lines
            if line.startswith('#'):
                continue

            args = [x.strip() for x in line.split(',')]

            if len(args) > 4:
                logger.error("Too many args, are you trying to run the normal import scholars file?")
                exit()
            roninAddr = args[0].replace("ronin:", "0x")
            discordID = args[1]
            scholarShare = round(float(args[2]), 3)

            if len(args) > 3:
                payoutAddr = args[3].replace("ronin:", "0x")
            else:
                payoutAddr = None

            seedNum, accountNum, currentCount = await getAccountNum(currentCount, roninAddr)

            name = await getNameFromDiscordID(discordID)
            res = await DB.addScholar(discordID, name, seedNum, accountNum, roninAddr, scholarShare)

            if payoutAddr is not None and payoutAddr != "":
                await DB.updateScholarAddress(discordID, payoutAddr)

            if not res["success"]:
                logger.error(f"failed to import scholar {discordID}")
                logger.error(res)
            else:
                count += 1
                logger.info(res['msg'])

    res = await DB.getAllScholars()
    if not res["success"]:
        logger.error("failed to get all scholars from database")
        exit()
    for row in res["rows"]:
        logger.info(f"{row['discord_id']}: seed/acc {row['seed_num']}/{row['account_num']} and share {row['share']}")
    logger.info(f"Imported {count} scholars")

    sys.exit("Done")


# 32 bit key, IV binary string, and ciphertext to decrypt
def decrypt(key, iv, ciphertext):
    assert len(key) == 32

    # convert IV to integer and create counter using the IV
    iv_int = int(binascii.hexlify(iv), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)

    # create cipher object
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    # decrypt ciphertext and return the decrypted binary string
    plaintext = aes.decrypt(ciphertext)
    return plaintext


async def getFromMnemonic():
    try:
        for a in range(len(mnemonicList)):
            accounts[a] = {}
            mnemonic = decrypt(decryptionKey, iv, mnemonicList[int(a)]).decode("utf8")
            for b in range(500):
                scholarAccount = Account.from_mnemonic(mnemonic, "", "m/44'/60'/0'/0/" + str(int(b)))
                accounts[a][scholarAccount.address.lower()] = b
        currentCount = 500
        return currentCount
    except Exception:
        logger.error("Exception in getFromMnemonic, not logging trace since key or passwords may be involved")
        return None


async def getMoreAddresses(currentCount):
    try:
        for a in range(len(mnemonicList)):
            mnemonic = decrypt(decryptionKey, iv, mnemonicList[int(a)]).decode("utf8")
            for b in range(250):
                scholarAccount = Account.from_mnemonic(mnemonic, "", "m/44'/60'/0'/0/" + str(int(b + currentCount)))
                accounts[a][scholarAccount.address.lower()] = b+currentCount
        currentCount += 250
        return currentCount
    except Exception:
        logger.error("Exception in getMoreAddresses, not logging trace since key or passwords may be involved")
        return None


async def getAccountNum(currentCount, address):
    seedNum = None
    accountNum = None
    for a in accounts:
        if address in accounts[a]:
            seedNum = a
            accountNum = accounts[a][address]
            break
    if currentCount >= 5000:
        logger.error("Could not get scholars address " + address + " from seeds. Something is wrong. Are you missing a seed phrase?")
        exit()
    if seedNum is None:
        currentCount = await getMoreAddresses(currentCount)
        return await getAccountNum(currentCount, address)
    return seedNum, accountNum, currentCount

try:
    x = decrypt(decryptionKey, iv, mnemonicList[0]).decode("utf8")
except:
    print(f"Password failed.")
    exit()

client.run(SeedStorage.DiscordBotToken)
