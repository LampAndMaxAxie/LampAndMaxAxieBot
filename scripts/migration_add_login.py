import asyncio
import aiosqlite as sql
from loguru import logger
from SeedStorage import *
from Common import *
import DB
import sys
import os

fName = "migrate_login.txt"

if len(sys.argv) > 1:
    fName = str(sys.argv[1])

if not os.path.exists(fName):
    print(f"File {fName} not found, please provide the migration file")
    exit()

@client.event
async def on_ready():
    await migration(fName) 


async def migration(fName):
    try:
        await DB.createMainTables()
    except:
        logger.error("Failed to create tables")
        exit()
    
    async with sql.connect(DB.MAIN_DB) as db:

        db.row_factory = sql.Row
        async with db.cursor() as c:

            await c.execute("SELECT * FROM users")
            rows = await c.fetchall()
            #for row in rows:
            #    out = "["
            #    for col in row:
            #        out += str(col) + ","
            #    out += "]"
            #    logger.info(out)

            await c.execute("BEGIN")
            try:
                await c.execute("ALTER TABLE users ADD COLUMN account_email TEXT")
                await c.execute("ALTER TABLE users ADD COLUMN account_pass TEXT")
                await c.execute("COMMIT")
                logger.success("Altered database schema")
            except:
                await c.execute("ROLLBACK")
                logger.error(f"Database schema already altered")

            await c.execute("BEGIN")
            try:
                count = 0
                with open(fName) as f:
                    for line in f:
                        # skip comment lines
                        if line.startswith('#'):
                            continue

                        try:
                            args = [x.strip() for x in line.split(',')]

                            discordID = args[0]
                            scholarAddr = args[1]
                            accountEmail = args[2]
                            accountPass = args[3]

                            res = await DB.updateScholarLogin(discordID, scholarAddr, accountEmail, accountPass)
                            if not res["success"]:
                                logger.error(f"failed to update scholar {discordID}, perhaps the ronin address doesn't match or the scholar doesn't exist")
                                logger.error(res)
                            else:
                                count += 1
                                logger.info(res['msg'])
                        except:
                            logger.error(f"failed to update an entry, perhaps bad input row data")

                await c.execute("COMMIT")
                logger.success(f"Performed migration successfully, updated {count} scholar logins")

            except:
                await c.execute("ROLLBACK")
                logger.error(f"Failed to perform migration")

        logger.success("Terminating!")
        exit()

client.run(DiscordBotToken)

