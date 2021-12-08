import traceback

import aiosqlite as sql
from loguru import logger

import Common

MAIN_DB = "axieBot.db"


# Common
@logger.catch
async def createMainTables():
    logger.info("in createMainTables")
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        logger.info("got connection")
        async with db.cursor() as c:
            logger.info("got cursor")
            await c.execute('''CREATE TABLE IF NOT EXISTS users 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, is_owner INTEGER, 
                 is_manager INTEGER, is_scholar INTEGER, discord_id INTEGER NOT NULL, seed_num INTEGER, 
                 account_num INTEGER, scholar_addr TEXT, payout_addr TEXT, share REAL, account_email TEXT, account_pass TEXT, 
                 created_at TIMESTAMP DEFAULT (strftime('%s', 'now')), updated_at TIMESTAMP DEFAULT (strftime('%s','now'))
                )''')
            await c.execute('''CREATE TABLE IF NOT EXISTS properties 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, property TEXT NOT NULL,
                 realVal REAL, textVal TEXT,
                 created_at TIMESTAMP DEFAULT (strftime('%s', 'now')), updated_at TIMESTAMP DEFAULT (strftime('%s','now'))
                )''')
            await c.execute('''CREATE TABLE IF NOT EXISTS slp_tracker 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, discord_id INTEGER NOT NULL, for_date TIMESTAMP NOT NULL,
                 total_slp INTEGER NOT NULL, adventure_slp INTEGER, arena_slp INTEGER, quest_slp INTEGER,
                 created_at TIMESTAMP DEFAULT (strftime('%s', 'now'))
                )''')
            await c.execute('''CREATE TABLE IF NOT EXISTS claims 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, claim_time TIMESTAMP NOT NULL,
                 total_slp INTEGER NOT NULL, ronin_addr TEXT NOT NULL, created_at TIMESTAMP DEFAULT (strftime('%s', 'now'))
                )''')
            logger.info("created tables")

            # set initial dev donation if it doesn't exist
            devDonation = await getProperty("devDonation", db)
            if devDonation["success"] and devDonation["rows"] is None:
                await setProperty("devDonation", 0.01)

            # set initial payout style
            massPay = await getProperty("massPay", db)
            if massPay["success"] and massPay["rows"] is None:
                await setProperty("massPay", 1)

            name = await Common.getNameFromDiscordID(Common.ownerID)
            await setOwner(Common.ownerID, name)
    pass


# Insert/Delete/Update

@logger.catch
async def addClaimLog(roninAddr, claimTimeStamp, totalSLP):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:

            await c.execute("BEGIN")
            try:
                await c.execute('''INSERT INTO claims
                    (ronin_addr, total_slp, claim_time) 
                    VALUES (?, ?, ?)''', (roninAddr, totalSLP, claimTimeStamp))
                await c.execute("COMMIT")

                logger.info(f"Logged claim history for {roninAddr}")

            except Exception:
                await c.execute("ROLLBACK")
                #logger.error(traceback.format_exc())
                logger.error(f"Failed to log claim for {roninAddr}")
                return {"success": False, "msg": f"Error in logging claim for {roninAddr}"}

    return {"success": True, "msg": f"Scholar logged claim {roninAddr}"}

@logger.catch
async def addScholar(discordID, name, seedNum, accountNum, roninAddr, share):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:
            rowsR = await getAllScholars(db)
            if rowsR["success"]:
                rows = rowsR["rows"]
            else:
                return rowsR

            userR = await getDiscordID(discordID, db)
            if userR is not None and "success" in userR and userR["success"]:
                user = userR["rows"]
            else:
                user = None
                # return userR

            for row in rows:
                if int(row['discord_id']) == int(discordID):
                    return {"success": False, "msg": "A scholar already exists with that discord ID"}
                if int(row['seed_num']) == seedNum and int(row['account_num']) == accountNum:
                    return {"success": False, "msg": "A scholar already exists with that seed/account"}

            await c.execute("BEGIN")
            try:
                if user is not None and int(user["discord_id"]) == int(discordID) and (user["is_scholar"] is None or int(user["is_scholar"]) == 0):
                    await c.execute('''UPDATE users SET is_scholar=1,seed_num=?,account_num=?,scholar_addr=?,share=?
                                where discord_id=?''', (seedNum, accountNum, roninAddr, share, discordID))
                else:
                    await c.execute('''INSERT INTO users 
                        (discord_id, name, is_scholar, seed_num, account_num, scholar_addr, share) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''', (discordID, name, 1, seedNum, accountNum, roninAddr, share))
                await c.execute("COMMIT")

                logger.info(f"Saved scholar {name}/{discordID} with seed/account/addr {seedNum}/{accountNum}/{roninAddr} and share {share}")

            except Exception:
                await c.execute("ROLLBACK")
                logger.error(traceback.format_exc())
                logger.error(f"Failed to save scholar {name}/{discordID}")
                return {"success": False, "msg": f"Error in processing scholar addition for {name}/{discordID}"}

    return {"success": True, "msg": f"Scholar {name}/{discordID} saved with seed/account/addr {seedNum}/{accountNum}/{roninAddr} and share={share}"}


@logger.catch
async def removeScholar(discordID):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:
            await c.execute("BEGIN")
            try:
                await c.execute('''UPDATE users SET is_scholar=0,seed_num=?,account_num=?,scholar_addr=?,share=?
                        WHERE discord_id=?''', (None, None, None, None, discordID))
                await c.execute("COMMIT")

                logger.info(f"Deleted scholar {discordID}")

            except:
                await c.execute("ROLLBACK")
                logger.error(f"Failed to delete scholar {discordID}")
                return {"success": False, "msg": f"Error in processing scholar deletion for {discordID}"}

    return {"success": True, "msg": f"Scholar {discordID} deleted"}


@logger.catch
async def updateScholarShare(discordID, share):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:
            userR = await getDiscordID(discordID, db)

            if userR is not None and "success" in userR and userR["success"]:
                user = userR["rows"]
            else:
                user = None
                # return userR

            if user is None:
                logger.error(f"Failed to update {discordID} because they are not in the database")
                return {"success": False, "msg": f"Failed to update {discordID} because they are not in the database"}

            if int(user["is_scholar"]) == 0:
                logger.error(f"Failed to update {discordID}'s scholar share because they are not a scholar")
                return {"success": False, "msg": f"Failed to update {discordID}'s scholar share because they are not a scholar"}

            await c.execute("BEGIN")
            try:
                await c.execute('''UPDATE users SET share=?
                        WHERE discord_id=?''', (share, discordID))
                await c.execute("COMMIT")

                logger.info(f"Updated {discordID}'s share to {share}")

            except:
                await c.execute("ROLLBACK")
                logger.error(f"Failed to update scholar {discordID}")
                return {"success": False, "msg": f"Error in processing scholar update for {discordID}"}

    return {"success": True, "msg": f"Scholar {discordID}'s share updated to {share * 100}%"}


@logger.catch
async def updateScholarAddress(discordID, addr):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:
            userR = await getDiscordID(discordID, db)

            if userR is not None and "success" in userR and userR["success"]:
                user = userR["rows"]
            else:
                user = None
                # return userR

            if user is None:
                logger.error(f"Failed to update {discordID} because they are not in the database")
                return {"success": False, "msg": f"Failed to update {discordID} because they are not in the database"}

            if user["is_scholar"] is None or int(user["is_scholar"]) == 0:
                logger.error(f"Failed to update {discordID}'s payout address because they are not a scholar")
                return {"success": False, "msg": f"Failed to update {discordID}'s payout address because they are not a scholar"}

            await c.execute("BEGIN")
            try:
                await c.execute('''UPDATE users SET payout_addr=?
                        WHERE discord_id=?''', (addr.replace('ronin:', '0x'), discordID))
                await c.execute("COMMIT")

                logger.info(f"Updated {discordID}'s payout address to {addr}")

            except:
                await c.execute("ROLLBACK")
                logger.error(f"Failed to update scholar {discordID}")
                return {"success": False, "msg": f"Error in processing scholar update for {discordID}"}

    return {"success": True, "msg": f"Scholar {discordID}'s payout address updated to {addr}"}


@logger.catch
async def updateScholarMainAddress(discordID, addr):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:
            userR = await getDiscordID(discordID, db)

            if userR is not None and "success" in userR and userR["success"]:
                user = userR["rows"]
            else:
                user = None
                # return userR

            logger.info(user)
            out = "["
            for col in user:
                out += str(col) + ","
            out += "]"
            logger.info(out)

            if user is None:
                logger.error(f"Failed to update {discordID} because they are not in the database")
                return {"success": False, "msg": f"Failed to update {discordID} because they are not in the database"}

            if user["is_scholar"] is None or int(user["is_scholar"]) == 0:
                logger.error(f"Failed to update {discordID}'s address because they are not a scholar")
                return {"success": False, "msg": f"Failed to update {discordID}'s scholar address because they are not a scholar"}

            await c.execute("BEGIN")
            try:
                await c.execute('''UPDATE users SET scholar_addr=?
                        WHERE discord_id=?''', (addr.replace('ronin:', '0x'), discordID))
                await c.execute("COMMIT")

                logger.info(f"Updated {discordID}'s scholar address to {addr}")

            except:
                await c.execute("ROLLBACK")
                logger.error(f"Failed to update scholar {discordID}")
                return {"success": False, "msg": f"Error in processing scholar update for {discordID}"}

    return {"success": True, "msg": f"Scholar {discordID}'s scholar address updated to {addr}"}


@logger.catch
async def updateScholarLogin(discordID, addr, email, password):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:
            userR = await getDiscordID(discordID, db)

            if userR is not None and "success" in userR and userR["success"]:
                user = userR["rows"]
            else:
                user = None
                # return userR

            #logger.info(user)
            #out = "["
            #for col in user:
            #    out += str(col) + ","
            #out += "]"
            #logger.info(out)

            if user is None:
                logger.error(f"Failed to update {discordID} because they are not in the database")
                return {"success": False, "msg": f"Failed to update {discordID} because they are not in the database"}

            if user["is_scholar"] is None or int(user["is_scholar"]) == 0:
                logger.error(f"Failed to update {discordID} because they are not a scholar")
                return {"success": False, "msg": f"Failed to update {discordID} because they are not a scholar"}

            await c.execute("BEGIN")
            try:
                await c.execute('''UPDATE users SET account_email = ?, account_pass = ?
                        WHERE discord_id = ? AND scholar_addr = ?''', (email, password, discordID, addr.replace('ronin:', '0x')))
                await c.execute("COMMIT")

                logger.info(f"Updated {discordID}'s scholar account login info updated")

            except:
                await c.execute("ROLLBACK")
                logger.error(f"Failed to update scholar {discordID}")
                return {"success": False, "msg": f"Error in processing scholar update for {discordID}"}

    return {"success": True, "msg": f"Scholar {discordID}'s scholar account login info updated"}


@logger.catch
async def addManager(discordID, name):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:
            userR = await getDiscordID(discordID, db)
            if userR is not None and "success" in userR and userR["success"]:
                user = userR["rows"]
            else:
                user = None
                # return userR

            if user is not None and int(user["discord_id"]) == int(discordID) and (user["is_manager"] is not None and int(user["is_manager"]) == 1):
                return {"success": False, "msg": "A manager already exists with that discord ID"}

            await c.execute("BEGIN")
            try:
                if user is not None and int(user["discord_id"]) == int(discordID) and (user["is_manager"] is None or int(user["is_manager"]) == 0):
                    await c.execute('''UPDATE users SET is_manager=1
                                WHERE discord_id=?''', (discordID,))
                else:
                    await c.execute('''INSERT INTO users 
                        (discord_id, name, is_manager) 
                        VALUES (?, ?, ?)''', (discordID, name, 1))
                await c.execute("COMMIT")

                logger.success(f"Saved manager {name}/{discordID}")

            except:
                await c.execute("ROLLBACK")
                logger.error(f"Failed to save manager {name}/{discordID}")
                return {"success": False, "msg": f"Error in processing manager addition for {name}/{discordID}"}

    return {"success": True, "msg": f"Manager {name}/{discordID} saved"}


@logger.catch
async def removeManager(discordID):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:
            await c.execute("BEGIN")
            try:
                await c.execute('''UPDATE users SET is_manager=0
                        WHERE discord_id=?''', (discordID,))
                await c.execute("COMMIT")

                logger.success(f"Deleted manager {discordID}")

            except:
                await c.execute("ROLLBACK")
                logger.error(f"Failed to delete manager {discordID}")
                return {"success": False, "msg": f"Error in processing manager deletion for {discordID}"}

    return {"success": True, "msg": f"Manager {discordID} deleted"}


@logger.catch
async def setOwner(discordID, name):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:
            rowsR = await getOwner(db)
            logger.info("rowsR:")
            logger.info(rowsR)

            if rowsR["success"]:
                owner = rowsR["rows"]
            else:
                owner = None
                # return rowsR

            userR = await getDiscordID(discordID, db)
            if userR is not None and "success" in userR and userR["success"]:
                user = userR["rows"]
            else:
                user = None
                # return userR

            if owner is not None:
                return {"success": False, "msg": "An owner already exists"}

            await c.execute("BEGIN")
            try:
                if user is not None and int(user["discord_id"]) == int(discordID):
                    await c.execute('''UPDATE users SET name=?,is_manager=1,is_owner=1
                                WHERE discord_id=?''', (name, discordID))
                else:
                    await c.execute('''INSERT INTO users 
                        (discord_id, name, is_manager, is_owner) 
                        VALUES (?, ?, ?, ?)''', (discordID, name, 1, 1))
                await c.execute("COMMIT")

                logger.info(f"Saved owner {name}/{discordID}")

            except:
                await c.execute("ROLLBACK")
                logger.error(f"Failed to save owner {name}/{discordID}")
                return {"success": False, "msg": f"Error in processing owner set for {name}/{discordID}"}

    return {"success": True, "msg": f"Owner {name}/{discordID} saved"}


@logger.catch
async def setProperty(prop, val):
    async with sql.connect(MAIN_DB) as db:
        db.row_factory = sql.Row
        async with db.cursor() as c:

            isNum = False
            if Common.isFloat(val):
                isNum = True

            await c.execute("BEGIN")
            try:
                res = await getProperty(prop, db)
                if res["success"] and res["rows"] is not None:
                    # update
                    if isNum:
                        await c.execute('''UPDATE properties SET realVal=?,textVal=?
                                WHERE property=?''', (val, None, prop))
                    else:
                        await c.execute('''UPDATE properties SET textVal=?,realVal=?
                                WHERE property=?''', (val, None, prop))

                elif res["success"] and res["rows"] is None:
                    # insert
                    if isNum:
                        await c.execute('''INSERT INTO properties 
                            (property, realVal) 
                            VALUES (?, ?)''', (prop, val))
                    else:
                        await c.execute('''INSERT INTO properties 
                            (property, textVal) 
                            VALUES (?, ?)''', (prop, val))
                else:
                    # error
                    await c.execute("ROLLBACK")
                    return res
            except:
                await c.execute("ROLLBACK")
                logger.error(f"Failed to save property {prop}")
                return {"success": False, "msg": f"Error in processing property set for {prop}"}

            await c.execute("COMMIT")
            return {"success": True, "msg": f"Successfully set {prop} to {val}"}


# Select
@logger.catch
async def getProperty(prop, db=None):
    created = False
    if db is None:
        db = await sql.connect(MAIN_DB)
        db.row_factory = sql.Row
        created = True
    c = await db.cursor()

    rows = None
    try:
        await c.execute("SELECT * FROM properties WHERE property=?", (prop,))
        rows = await c.fetchone()
        logger.info(f"Fetched property: {prop}")

    except:
        logger.error(f"Failed to get property: {prop}")

        if created:
            await c.close()
            await db.close()

        return {"success": False, "msg": f"Exception in processing property query"}

    if created:
        await c.close()
        await db.close()

    return {"success": True, "rows": rows}

@logger.catch
async def getLastClaim(roninAddr, db=None):
    created = False
    if db is None:
        db = await sql.connect(MAIN_DB)
        db.row_factory = sql.Row
        created = True
    c = await db.cursor()

    rows = None
    try:
        await c.execute("SELECT * FROM claims WHERE ronin_addr = ? ORDER BY claim_time DESC", (roninAddr,))
        rows = await c.fetchone()
        #logger.info(f"Got last claim data for {roninAddr}")

    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"Failed to get last claim for {roninAddr}")
        return {"success": False, "msg": f"Error in getting claim for {roninAddr}"}

    return {"success": True, "rows": rows}

@logger.catch
async def getAllScholars(db=None):
    created = False
    if db is None:
        db = await sql.connect(MAIN_DB)
        db.row_factory = sql.Row
        created = True
    c = await db.cursor()

    rows = None
    try:
        await c.execute("SELECT * FROM users WHERE is_scholar=1")
        rows = await c.fetchall()
        logger.info(f"Fetched all scholars")

    except:
        logger.error(f"Failed to get all scholars")

        if created:
            await c.close()
            await db.close()

        return {"success": False, "msg": f"Exception in processing scholar query"}

    if created:
        await c.close()
        await db.close()

    return {"success": True, "rows": rows}


@logger.catch
async def getAllScholarsByIndex(seed, minIndex=None, maxIndex=None, db=None):
    created = False
    if db is None:
        db = await sql.connect(MAIN_DB)
        db.row_factory = sql.Row
        created = True
    c = await db.cursor()

    if minIndex is None or maxIndex is None:
        maxIndex = 0
        minIndex = 0

    rows = None
    try:
        if minIndex == 0 or maxIndex == 0:
            await c.execute("SELECT * FROM users WHERE is_scholar=1 AND seed_num = ?", (int(seed),))
        else:
            await c.execute("SELECT * FROM users WHERE is_scholar=1 AND seed_num = ? AND account_num >= ? AND account_num <= ?", (int(seed), int(minIndex), int(maxIndex)))
        rows = await c.fetchall()
        logger.info(f"Fetched all scholars with seed={seed} and account range {minIndex}-{maxIndex}")

    except Exception as e:
        logger.error(f"Failed to get all scholars in range")
        logger.error(e)

        if created:
            await c.close()
            await db.close()

        return {"success": False, "msg": f"Exception in processing scholar query"}

    if created:
        await c.close()
        await db.close()

    return {"success": True, "rows": rows}


@logger.catch
async def getAllManagers(db=None):
    created = False
    if db is None:
        db = await sql.connect(MAIN_DB)
        db.row_factory = sql.Row
        created = True
    c = await db.cursor()

    rows = None
    try:
        await c.execute("SELECT * FROM users WHERE is_manager=1")
        rows = await c.fetchall()
        logger.info(f"Fetched all managers")

    except:
        logger.error(f"Failed to get all managers")

        if created:
            await c.close()
            await db.close()

        return {"success": False, "msg": f"Exception in processing manager query"}

    if created:
        await c.close()
        await db.close()

    return {"success": True, "rows": rows}


@logger.catch
async def getAllNoRole(db=None):
    created = False
    if db is None:
        db = await sql.connect(MAIN_DB)
        db.row_factory = sql.Row
        created = True
    c = await db.cursor()

    rows = None
    try:
        await c.execute("SELECT * FROM users WHERE (is_manager=0 OR is_manager IS NULL) AND (is_scholar=0 OR is_scholar IS NULL) AND (is_owner=0 OR is_owner IS NULL)")
        rows = await c.fetchall()
        logger.info(f"Fetched all users with no role")

    except:
        logger.error(f"Failed to get all users with no role")

        if created:
            await c.close()
            await db.close()

        return {"success": False, "msg": f"Exception in processing no roles query"}

    if created:
        await c.close()
        await db.close()

    return {"success": True, "rows": rows}


@logger.catch
async def getAllUsers(db=None):
    created = False
    if db is None:
        db = await sql.connect(MAIN_DB)
        db.row_factory = sql.Row
        created = True
    c = await db.cursor()

    rows = None
    try:
        await c.execute("SELECT * FROM users")
        rows = await c.fetchall()
        logger.info(f"Fetched all users")

    except:
        logger.error(f"Failed to get all users")

        if created:
            await c.close()
            await db.close()

        return {"success": False, "msg": f"Exception in processing all users query"}

    if created:
        await c.close()
        await db.close()

    return {"success": True, "rows": rows}


@logger.catch
async def getAllManagerIDs(db=None):
    created = False
    if db is None:
        db = await sql.connect(MAIN_DB)
        db.row_factory = sql.Row
        created = True
    c = await db.cursor()

    rows = None
    try:
        await c.execute("SELECT * FROM users WHERE is_manager=1 or is_owner=1")
        rows = await c.fetchall()
        logger.info(f"Fetched all managers")

    except:
        logger.error(f"Failed to get all managers")

        if created:
            await c.close()
            await db.close()

        return {"success": False, "msg": f"Exception in processing manager query"}

    ids = []
    for row in rows:
        ids.append(int(row["discord_id"]))

    if created:
        await c.close()
        await db.close()

    return ids


@logger.catch
async def getDiscordID(discordID, db=None):
    created = False
    if db is None:
        db = await sql.connect(MAIN_DB)
        db.row_factory = sql.Row
        created = True
    c = await db.cursor()

    rows = None
    try:
        await c.execute("SELECT * FROM users WHERE discord_id=? LIMIT 1", (int(discordID),))
        rows = await c.fetchone()
        logger.info(f"Fetched discord ID {discordID}")
        out = "["
        for col in rows:
            out += str(col) + ","
        out += "]"
        logger.info(out)

    except Exception:
        logger.warning(f"Failed to get discord ID {discordID}, not in database")
        # logger.error(e)

        if created:
            await c.close()
            await db.close()

        return {"success": False, "msg": f"Exception in processing discord ID query"}

    if created:
        await c.close()
        await db.close()

    return {"success": True, "rows": rows}


@logger.catch
async def getOwner(db=None):
    created = False
    if db is None:
        db = await sql.connect(MAIN_DB)
        db.row_factory = sql.Row
        created = True
    c = await db.cursor()

    logger.info("before async in getOwner")
    rows = None
    try:
        logger.info("exec owner query")
        await c.execute("SELECT * FROM users WHERE is_owner=1 LIMIT 1")
        rows = await c.fetchone()
        logger.info("fetched owner")
        logger.info(f"Fetched owner")

    except Exception as e:
        logger.error(f"Failed to get owner")
        logger.error(e)

        if created:
            await c.close()
            await db.close()

        return {"success": False, "msg": f"Exception in processing owner query"}

    if created:
        await c.close()
        await db.close()

    return {"success": True, "rows": rows}


@logger.catch
async def isManager(discordID):
    mgrs = await getAllManagers()

    for row in mgrs["rows"]:
        if int(row['discord_id']) == int(discordID):
            return True

    return await isOwner(discordID)


@logger.catch
async def isOwner(discordID):
    owner = await getOwner()

    if int(owner["rows"]['discord_id']) == int(discordID):
        return True

    return False


@logger.catch
async def getMembershipReport():
    try:
        mgrs = await getAllManagers()
        sclr = await getAllScholars()
        norl = await getAllNoRole()
        totl = await getAllUsers()
        ownr = await getOwner()

        logger.info(norl)

        mgrs = 0 if mgrs["rows"] is None else len(mgrs["rows"])
        sclr = 0 if sclr["rows"] is None else len(sclr["rows"])
        norl = 0 if norl["rows"] is None else len(norl["rows"])
        totl = 0 if totl["rows"] is None else len(totl["rows"])
        ownr = 1 if ownr is not None else 0
        logger.info(norl)

    except:
        logger.error("Error processing membership report")
        return {"success": False, "msg": "Error processing membership report"}

    return {"success": True, "managers": mgrs, "scholars": sclr, "noRole": norl, "owner": ownr, "total": totl}
