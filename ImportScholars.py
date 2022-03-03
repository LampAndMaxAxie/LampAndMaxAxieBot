import DB
from Common import *
from SeedStorage import *

fName = "import.txt"

if len(sys.argv) > 1:
    fName = str(sys.argv[1])

if not os.path.exists(fName):
    print(f"File {fName} not found, please provide the import file")
    sys.exit()


@client.event
async def on_ready():
    await importScholars(fName) 


async def importScholars(fName):
    try:
        await DB.createMainTables()
    except:
        logger.error("Failed to create tables")
        sys.exit()

    count = 0
    with open(fName) as f:
        for line in f:
            # skip comment lines
            if line.startswith('#'):
                continue
            line = line.replace("\ufeff", "")
            args = [x.strip() for x in line.split(',')]

            seedNum = args[0]
            accountNum = args[1]
            roninAddr = args[2].replace("ronin:", "0x").strip()
            discordID = args[3]
            scholarShare = round(float(args[4]), 3)

            if len(args) > 5:
                payoutAddr = args[5].replace("ronin:", "0x").strip()
            else:
                payoutAddr = None

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
        sys.exit()
    for row in res["rows"]:
        logger.info(f"{row['discord_id']}: seed/acc {row['seed_num']}/{row['account_num']} and share {row['share']}")
    logger.info(f"Imported {count} scholars")

    sys.exit()

client.run(DiscordBotToken)
