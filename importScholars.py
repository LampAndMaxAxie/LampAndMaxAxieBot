import asyncio
import aiosqlite as sql
from loguru import logger
from SecretStorage import *
from Common import *
import DB

fName = "import.txt"


@client.event
async def on_ready():
    await importScholars(fName) 


async def importScholars(fName):
    try:
        await DB.createMainTables()
    except:
        logger.error("Failed to create tables")
        exit()

    count = 0
    with open(fName) as f:
        for line in f:
            # skip comment lines
            if line.startswith('#'):
                continue

            args = [x.strip() for x in line.split(',')]

            seedNum = args[0]
            accountNum = args[1]
            discordID = args[2]
            scholarShare = round(float(args[3]),3)
            name = await getNameFromDiscordID(discordID)

            res = await DB.addScholar(discordID, name, seedNum, accountNum, scholarShare)
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

    exit()

client.run(DiscordBotToken)

