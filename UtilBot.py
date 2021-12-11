# Author: Michael Conard
# Purpose: An Axie Infinity utility bot. Gives QR codes and daily progress/alerts.

import datetime
import json
import math
import os
import os.path
import sys
import time
import traceback
import urllib

import asyncio
import discord
import numpy as np
import pandas as pd
import pytz
import qrcode
import requests
import urllib3
from PIL import Image
from loguru import logger
from urllib3 import Retry

import AccessToken
import Common
import DB

try:
    CACHE_TIME = int(Common.config.get('Bot', 'cacheTimeMinutes'))

    if int(CACHE_TIME) < 30:
        logger.warning("Configured cache time invalid, setting to 30 minutes")
        CACHE_TIME = 30

    tz1String = Common.config.get('Bot', 'timezone1')
    tz2String = Common.config.get('Bot', 'timezone2')
    tz1 = pytz.timezone(tz1String)
    tz2 = pytz.timezone(tz2String)
    tzutc = pytz.timezone('UTC')
except:
    logger.error("Please fill out a [Bot] section with cacheTimeMinutes, timezone1, and timezone2.")
    exit()

scholarCache = {}
summaryCache = {}
battlesCache = {}
teamCache = {}

slpEmojiID = {}

graphQL = "https://graphql-gateway.axieinfinity.com/graphql"
gameAPI = "https://game-api.skymavis.com/game-api"


def getQRCode(accessToken, discordID):
    # Function to create a QRCode from the accessToken

    # Make an image as a QR Code from the accessToken
    img = qrcode.make(accessToken)
    # Save the image
    imgName = "./qr/" + str(discordID) + 'QRCode.png'
    img.save(imgName)
    return imgName


# setup requests pool
retryAmount = 3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
retries = Retry(connect=retryAmount, read=retryAmount, redirect=2, status=retryAmount, status_forcelist=[502, 503])
http = urllib3.PoolManager(retries=retries)


async def getMarketplaceProfile(address):
    try:
        url = "https://axieinfinity.com/graphql-server-v2/graphql?query={publicProfileWithRoninAddress(roninAddress:\"" + address + "\"){accountId,name}}"
        payload = {}
        headers = {
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)',
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        jsonDat = json.loads(response.text)
    except Exception as e:
        logger.error("Error in getMarketplaceProfile")
        logger.error(e)
        await sendErrorToManagers(e, "")

        return None

    return jsonDat


async def getInGameName(address):
    dat = await getMarketplaceProfile(address)
    if dat is None:
        return None

    return dat['data']['publicProfileWithRoninAddress']['name']


async def sendErrorToManagers(e, flag):
    tb = traceback.format_exc()
    lineNumber = str(sys.exc_info()[-1].tb_lineno)

    if flag != "":
        msg = f"On {flag}:\n"
    else:
        msg = ""

    msg += f"Caught exception: {e} on line {lineNumber}\n"
    msg += f"```\n{tb}\n```"

    mgrIds = await DB.getAllManagerIDs()

    await Common.messageManagers(msg, mgrIds)


def getEmojiFromReact(reaction):
    emoji = None
    if type(reaction.emoji) is str:
        emoji = reaction.emoji
    else:
        emoji = reaction.emoji.name
    return emoji


async def getKeyForUser(user):
    seedNum = user["seed_num"]
    accountNum = user["account_num"]
    scholarAddr = user["scholar_addr"]
    ret = await Common.getFromMnemonic(seedNum, accountNum, scholarAddr)

    if ret is None:
        return None, None

    return ret["key"], ret["address"]


def is_int(val):
    try:
        num = int(val)
    except ValueError:
        return False
    return True


# fetch a remote image
def saveUrlImage(url, name):
    try:
        urllib.request.urlretrieve(url, name)
        return name
    except:
        logger.error("Erroring downloading image " + url)
        return None


def concatImages(imagePaths, name, excessPxl=0):
    try:
        images = [Image.open(x) for x in imagePaths]
        widths, heights = zip(*(i.size for i in images))

        total_width = sum(widths) + excessPxl
        max_height = max(heights)

        new_im = Image.new('RGBA', (total_width, max_height), (0, 0, 0, 0))

        x_offset = excessPxl
        for im in images:
            new_im.paste(im, (x_offset, 0))
            x_offset += im.size[0]

        new_im.save(name)
        return name
    except:
        logger.error("Error combining images")
        return None


# get a player's Axie Infinity game-api auth/bearer token
def getPlayerToken(roninKey, roninAddr):
    token = ""
    tokenBook = {}
    try:
        changed = False

        # make the caching file if it doesn't exist
        if not os.path.exists("jwtTokens.json"):
            f = open("jwtTokens.json", 'w')
            f.write("{}")
            f.close()
            changed = True

        with open("jwtTokens.json") as f:
            tokenBook = json.load(f)

            # check if cached token is available and not-expired for player
            if roninAddr in tokenBook and int(tokenBook[roninAddr]["exp"]) > int(time.time()):
                token = tokenBook[roninAddr]["token"]
            else:
                # generate new token
                token = AccessToken.GenerateAccessToken(roninKey, roninAddr)
                exp = int(time.time()) + 6 * 24 * 60 * 60  # 6 day expiration, to be shy of 7 days
                tokenBook[roninAddr] = {"token": token, "exp": exp}
                changed = True

        if changed:
            # save the tokens
            with open("jwtTokens.json", 'w') as f:
                json.dump(tokenBook, f)
    except:
        logger.error("Failed to get token for: " + roninAddr)
        logger.error(traceback.format_exc())
        return None
    return token


# make an API request and process the result as JSON data
async def makeJsonRequestWeb(url):
    response = None
    jsonDat = None
    try:
        response = http.request(
            "GET",
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
                "Accept": "*/*",
            }
        )

        jsonDat = json.loads(response.data.decode('utf8'))  # .decode('utf8')
        succ = False
        if 'success' in jsonDat:
            succ = jsonDat['success']

        if 'story_id' in jsonDat:
            succ = True

        if not succ:
            if 'details' in jsonDat and len(jsonDat['details']) > 0:
                if 'code' in jsonDat:
                    logger.error("API call failed in makeJsonRequest for: " + url + ", " + jsonDat['code'])
                else:
                    logger.error("API call failed in makeJsonRequest for: " + url + ", " + jsonDat['details'][0])
            else:
                logger.error("API call failed in makeJsonRequest for: " + url)
            return None

    except Exception as e:
        logger.error("Exception in makeJsonRequest for: " + url)
        logger.error(response.data.decode('utf8'))
        # traceback.print_exc()

        await sendErrorToManagers(e, url)

        return None

    return jsonDat


# make an Axie Infinity game-api authorized request and process the result as JSON data
async def makeJsonRequest(url, token, attempt=0):
    response = None
    jsonDat = None
    try:
        response = http.request(
            "GET",
            url,
            headers={
                "Host": "game-api.skymavis.com",
                "User-Agent": "UnityPlayer/2019.4.28f1 (UnityWebRequest/1.0, libcurl/7.52.0-DEV)",
                "Accept": "*/*",
                "Accept-Encoding": "identity",
                "Authorization": 'Bearer ' + token,
                "X-Unity-Version": "2019.4.28f1"
            }
        )

        jsonDat = json.loads(response.data.decode('utf8'))  # .decode('utf8')
        succ = False
        if 'success' in jsonDat:
            succ = jsonDat['success']

        if 'story_id' in jsonDat:
            succ = True

        if not succ:
            if 'details' in jsonDat and len(jsonDat['details']) > 0:
                if 'code' in jsonDat:
                    logger.error(f"API call failed in makeJsonRequest for: {url}, {jsonDat['code']}, attempt {attempt}")
                else:
                    logger.error(f"API call failed in makeJsonRequest for: {url}, {jsonDat['details'][0]}, attempt {attempt}")
            else:
                logger.error(f"API call failed in makeJsonRequest for: {url}, attempt {attempt}")

            if attempt < 3:
                return await makeJsonRequest(url, token, attempt + 1)
            else:
                return None

    except Exception as e:
        logger.error(f"Exception in makeJsonRequest for: {url}, attempt {attempt}")
        logger.error(response.data.decode('utf8'))
        # traceback.print_exc()

        if attempt < 3:
            return await makeJsonRequest(url, token, attempt + 1)
        else:
            await sendErrorToManagers(e, url)
            return None

    return jsonDat


# get a player's daily stats and progress
async def getPlayerDailies(discordId, targetId, discordName, roninKey, roninAddr, guildId=None):
    global scholarCache

    # check caching
    # print(scholarCache)
    # print(targetId)
    if targetId in scholarCache and int(scholarCache[targetId]["cache"]) - int(time.time()) > 0:
        if scholarCache[targetId]["data"] is not None:
            return scholarCache[targetId]["data"]

    # get auth token
    token = getPlayerToken(roninKey, roninAddr)
    if token is None:
        logger.error(f"Failed to get auth token for daily for {roninAddr}")
        return None

    # fetch data
    url = gameAPI + "/clients/" + roninAddr + "/player-stats"
    jsonDat = await makeJsonRequest(url, token)

    urlQuests = gameAPI + "/clients/" + roninAddr + "/quests"
    jsonDatQuests = await makeJsonRequest(urlQuests, token)

    urlBattle = gameAPI + "/leaderboard?client_id=" + roninAddr + "&offset=0&limit=0"
    jsonDatBattle = await makeJsonRequest(urlBattle, token)

    urlBalance = gameAPI + "/clients/" + roninAddr + "/items/1"
    jsonDatBalance = await makeJsonRequest(urlBalance, token)

    # fail out if any data is missing
    if jsonDat is None or jsonDatQuests is None or jsonDatBattle is None or jsonDatBalance is None:
        logger.error(f"Failed an API call for daily for {roninAddr}")
        return None

    cacheExp = int(time.time()) + CACHE_TIME * 60
    try:
        meta = jsonDat['meta_data']
        jsonDat = jsonDat['player_stat']

        utc_time = int(datetime.datetime.now(tzutc).timestamp())
        cacheExp = utc_time + CACHE_TIME * 60

        # process data

        maxEnergy = meta['max_energy']
        maxSlp = meta['max_slp_by_day']

        daysSinceCreated = round((utc_time - int(float(jsonDat['created_at']))) / (60 * 60 * 24), 1)
        lastUpdatedStamp = int(jsonDat['updated_at'])
        lastUpdatedEast = datetime.datetime.fromtimestamp(lastUpdatedStamp).replace(tzinfo=tzutc).astimezone(tz1)
        lastUpdatedPhil = datetime.datetime.fromtimestamp(lastUpdatedStamp).replace(tzinfo=tzutc).astimezone(tz2)

        # player-stats, energy/daily SLP/match counts
        remainingEnergy = int(jsonDat['remaining_energy'])
        pvpSlp = int(jsonDat['pvp_slp_gained_last_day'])
        pveSlp = int(jsonDat['pve_slp_gained_last_day'])
        pvpCount = int(jsonDat['pvp_battle_number_last_day'])
        pveCount = int(jsonDat['pve_battle_number_last_day'])
        pvpLastPlayed = round((utc_time - int(jsonDat['last_played_pvp_at'])) / (60 * 60), 1)
        pvpStreakLost = int(jsonDat['pvp_last_streak_lost'])

        # quests, quest completion data and progress
        quest = jsonDatQuests['items'][0]
        questClaimed = quest['claimed'] is not None
        checkIn = quest['missions'][0]['is_completed']
        pveQuest = quest['missions'][1]['progress']
        pveCount = pveQuest  # temporary
        pveQuestN = quest['missions'][1]['total']
        pvpQuest = quest['missions'][2]['progress']
        pvpCount = pvpQuest  # temporary
        pvpQuestN = quest['missions'][2]['total']
        questSlp = 0
        questCompleted = pveQuest >= pveQuestN and pvpQuest >= pvpQuestN and checkIn
        if questCompleted and questClaimed:
            questSlp = 25

        # sometimes it returns 0 energy if they haven't done anything yet
        if questSlp == 0 and remainingEnergy == 0 and pvpCount == 0 and pveCount == 0 and pveSlp == 0:
            if maxEnergy is not None and maxEnergy > 0:
                remainingEnergy = maxEnergy
            else:
                remainingEnergy = 20

        # battle data. mmr/rank/wins etc
        player = jsonDatBattle['items'][1]
        name = player["name"]
        mmr = int(player["elo"])
        rank = int(player["rank"])
        wins = int(player["win_total"])
        losses = int(player["lose_total"])
        draws = int(player["draw_total"])

        winRate = "0%"
        if wins + losses + draws > 0:
            winRate = str(round(wins / (wins + losses + draws), 2)) + "%"

        # items, account/lifetime/earned SLP and claim date
        lifetimeSlp = jsonDatBalance["blockchain_related"]["checkpoint"]
        if lifetimeSlp is None:
            lifetimeSlp = 0
        else:
            lifetimeSlp = int(lifetimeSlp)

        totalSlp = int(jsonDatBalance["total"])
        roninSlp = jsonDatBalance["blockchain_related"]["balance"]
        claimableSlp = jsonDatBalance["claimable_total"]
        if roninSlp is None:
            roninSlp = 0
        else:
            roninSlp = int(roninSlp)

        if totalSlp - roninSlp - claimableSlp < 0:
            inGameSlp = int(totalSlp - claimableSlp)
        else:
            inGameSlp = int(totalSlp - roninSlp - claimableSlp)

        lastClaim = tz1.fromutc(datetime.datetime.fromtimestamp(int(jsonDatBalance["last_claimed_item_at"])))
        lastClaimStamp = int(jsonDatBalance["last_claimed_item_at"])
        nextClaimStamp = lastClaimStamp + (14 * 24 * 60 * 60)
        daysSinceClaim = math.ceil((utc_time - int(jsonDatBalance["last_claimed_item_at"])) / (60 * 60 * 24))
        claimDate = tz1.fromutc(
            datetime.datetime.fromtimestamp(int(jsonDatBalance["last_claimed_item_at"]) + (14 * 24 * 60 * 60)))

        daysRemaining = 14 - daysSinceClaim
        if daysRemaining < 0:
            daysRemaining = 0
        claimText = str(claimDate)[:len(str(claimDate)) - 6] + ' - ({} days)'.format(daysRemaining)

        pvpText = "0"
        pveText = "0"
        if pvpCount > 0:
            pvpText = str(round(float(pvpSlp) / float(pvpCount), 2))
        if pveCount > 0:
            pveText = str(round(float(pveSlp) / float(pveCount), 2))

        questTxt = ""
        if questCompleted and questClaimed:
            questTxt = "completed and claimed"
        elif questCompleted and not questClaimed:
            questTxt = "completed but not claimed"
        elif not questCompleted:
            questTxt = "incomplete"

        checkInTxt = "complete" if checkIn else "incomplete"

        updatedTxt = "`" + str(lastUpdatedEast) + '`\n`' + str(lastUpdatedPhil) + '`\n'

        cacheEast = datetime.datetime.fromtimestamp(int(cacheExp)).replace(tzinfo=tzutc).astimezone(tz1)
        cachePhil = datetime.datetime.fromtimestamp(int(cacheExp)).replace(tzinfo=tzutc).astimezone(tz2)

        cacheTxt = "`" + str(cacheEast) + '`\n`' + str(cachePhil) + '`\n'

        slpPerDay = round(inGameSlp / daysSinceClaim, 1)
        pveTxt = str(pveQuest) + '/' + str(pveQuestN)
        pvpTxt = str(pvpQuest) + '/' + str(pvpQuestN)

        slpIcon = None
        if guildId and guildId in slpEmojiID:
            if slpEmojiID[guildId] is not None:
                slpIcon = '<:slp:{}>'.format(slpEmojiID[guildId])
        if slpIcon is None:
            slpIcon = ""

        if Common.hideScholarRonins:
            roninAddr = "<hidden>"

        embed = discord.Embed(title="Scholar Daily Stats", description="Daily stats for scholar " + discordName,
                              timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
        embed.add_field(name=":book: Scholar Name", value=f"{name}")
        embed.add_field(name=":house: Ronin Address", value=f"{roninAddr}")
        embed.add_field(name=":baggage_claim: Next Claim Ready", value=f"<t:{nextClaimStamp}:R>")
        embed.add_field(name="Lifetime SLP", value=f"{lifetimeSlp} {slpIcon}")
        embed.add_field(name="Current SLP", value=f"{inGameSlp} {slpIcon}")
        embed.add_field(name="Avg SLP/Day", value=f"{slpPerDay} {slpIcon}")
        embed.add_field(name=":crossed_swords: Arena MMR", value=f"{mmr}")
        embed.add_field(name=":trophy: Arena Rank", value=f"{rank}")
        embed.add_field(name=":cloud_lightning: Remaining Energy", value=f"{remainingEnergy}")
        embed.add_field(name=":white_check_mark: Quest - Check in", value=f"{checkInTxt}")
        embed.add_field(name=":bear: Quest - PvE", value=f"{pveTxt}, {pveSlp}/50 SLP")
        embed.add_field(name=":bow_and_arrow: Quest - PvP", value=f"{pvpTxt}")
        embed.add_field(name=":scroll: Daily Quest", value=f"{questTxt}")
        embed.add_field(name=":clock1: Last Updated", value=f"<t:{lastUpdatedStamp}:f>")
        embed.add_field(name=":floppy_disk: Uncache Timer", value=f"<t:{cacheExp}:R>")

        # package the data to cache and return
        res = {
            "embed": embed,
            "mmr": mmr,
            "rank": rank,
            "name": name,
            "pvpSlp": pvpSlp,
            "pveSlp": pveSlp,
            "pvpCount": pvpCount,
            "pveCount": pveCount,
            "questSlp": questSlp,
            "totalSlp": pveSlp + pvpSlp + questSlp,
            "energy": remainingEnergy,
            "lifetimeSlp": lifetimeSlp,
            "claimCycleDays": daysSinceClaim,
            "inGameSlp": inGameSlp,
            "avgSlpPerDay": round(inGameSlp / daysSinceClaim, 1),
            "claimDate": claimDate
        }
    except Exception as e:
        # traceback.print_exc()
        logger.error(e)
        logger.error(traceback.format_exc())
        await sendErrorToManagers(e, discordName)

        return None

    # save to the cache
    scholarCache[targetId] = {"data": res, "cache": cacheExp}

    return res


# returns data on scholar's battles
async def getRoninBattles(roninAddr):
    global battlesCache

    # check caching
    if roninAddr in battlesCache and int(battlesCache[roninAddr]["cache"]) - int(time.time()) > 0:
        return battlesCache[roninAddr]["data"]

    # fetch data
    url = gameAPI + "/clients/" + roninAddr + "/battles?offset=0&limit=0&battle_type=0"
    jsonDat = await makeJsonRequest(url, "none")

    urlRank = gameAPI + "/leaderboard?client_id=" + roninAddr + "&offset=0&limit=0"
    jsonDatRank = await makeJsonRequest(urlRank, "none")

    name = await getInGameName(roninAddr)
    if name is None:
        name = "<unknown>"

    # fail out if any data is missing
    if jsonDat is None or jsonDatRank is None:
        return None

    cacheExp = int(time.time()) + CACHE_TIME * 60
    res = None
    try:
        battles = jsonDat['items']

        # Arena data, mmr/rank
        player = jsonDatRank['items'][1]
        name = player["name"]
        mmr = int(player["elo"])
        rank = int(player["rank"])

        utc_time = int(datetime.datetime.now(tzutc).timestamp())
        cacheExp = utc_time + CACHE_TIME * 60

        streakType = None
        streakBroken = False
        streakAmount = 0
        axieIds = []

        wins = 0
        losses = 0
        draws = 0
        lastTime = None
        latestMatches = []
        for battle in battles:
            result = None

            if lastTime is None:
                lastTime = datetime.datetime.strptime(battle['created_at'], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=tzutc)

            # opponent ronin
            opponent = None
            pos = None
            if battle['first_client_id'] == roninAddr:
                opponent = battle['second_client_id']
                pos = 0
                if len(axieIds) == 0:
                    teamId = battle['first_team_id']
                    for axie in battle['fighters']:
                        if axie['team_id'] == teamId:
                            axieIds.append(axie['fighter_id'])
            else:
                opponent = battle['first_client_id']
                pos = 1
                if len(axieIds) == 0:
                    teamId = battle['second_team_id']
                    for axie in battle['fighters']:
                        if axie['team_id'] == teamId:
                            axieIds.append(axie['fighter_id'])

            # count draw
            if battle['winner'] == 2:
                draws += 1
                result = 'draw'
            # count win
            elif battle['winner'] == pos:
                wins += 1
                result = 'win'
            # count loss
            else:
                losses += 1
                result = 'lose'

            # streak
            if streakBroken:
                pass
            elif streakType is None:
                streakType = result
                streakAmount = 1
            elif not streakBroken and streakType == result:
                streakAmount += 1
            elif not streakBroken and streakType != result:
                streakBroken = True

            # opponent ronin
            opponent = None
            if battle['first_client_id'] == roninAddr:
                opponent = battle['second_client_id']
            else:
                opponent = battle['first_client_id']

            if len(latestMatches) < 5:
                latestMatches.append({'result': result,
                                      'replay': 'https://cdn.axieinfinity.com/game/deeplink.html?f=rpl&q={}'.format(
                                          battle['battle_uuid']), 'opponent': opponent})

        axieImages = []
        combinedImg = None
        combinedIds = None
        imgErr = False
        for axieId in axieIds:
            imgPath = './images/{}.png'.format(axieId)
            if os.path.exists(imgPath):
                axieImages.append(imgPath)
            else:
                axieUrl = 'https://storage.googleapis.com/assets.axieinfinity.com/axies/{}/axie/axie-full-transparent.png'.format(
                    axieId)
                res = saveUrlImage(axieUrl, imgPath)
                if res is None:
                    imgErr = True
                    break
                else:
                    axieImages.append(imgPath)

        if not imgErr:
            combinedIds = '{}-{}-{}.png'.format(axieIds[0], axieIds[1], axieIds[2])
            combinedImg = './images/{}-{}-{}.png'.format(axieIds[0], axieIds[1], axieIds[2])
            if not os.path.exists(combinedImg):
                res = concatImages(axieImages, combinedImg)
                if res is None:
                    imgErr = True

        matches = wins + losses + draws

        if matches == 0:
            return None

        winrate = 0
        loserate = 0
        drawrate = 0
        if matches > 0:
            winrate = round(wins / matches * 100, 2)
            loserate = round(losses / matches * 100, 2)
            drawrate = round(draws / matches * 100, 2)

        replayText = ""
        resultText = ""
        count = 1
        for match in latestMatches:
            resultText += match['result'] + '\n'
            replayText += '[Replay {}]({})\n'.format(count, match['replay'])
            count += 1

        streakText = "Current " + streakType.capitalize() + " Streak"

        cacheEast = datetime.datetime.fromtimestamp(int(cacheExp)).replace(tzinfo=tzutc).astimezone(tz1)
        cachePhil = datetime.datetime.fromtimestamp(int(cacheExp)).replace(tzinfo=tzutc).astimezone(tz2)
        cacheTxt = "`" + str(cacheEast)[:len(str(cacheEast)) - 6] + '`\n`' + str(cachePhil)[:len(str(cachePhil)) - 6] + '`\n'

        lastEast = lastTime.astimezone(tz1)
        lastPhil = lastTime.astimezone(tz2)
        lastTxt = "`" + str(lastEast)[:len(str(lastEast)) - 6] + '`\n`' + str(lastPhil)[:len(str(lastPhil)) - 6] + '`\n'

        embed = discord.Embed(title="Account Recent Battles", description="Recent battles for address " + roninAddr,
                              timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
        embed.add_field(name=":book: In Game Name", value=f"{name}")
        embed.add_field(name=":clock1: Last Match Time", value=f"<t:{lastTime}:R>")
        embed.add_field(name=":anger: Arena Matches", value=f"{matches}, last ~7 days")
        embed.add_field(name=":crossed_swords: Arena MMR", value=f"{mmr}")
        embed.add_field(name=":trophy: Arena Rank", value=f"{rank}")
        embed.add_field(name=f":pencil: {streakText}", value=f"{streakAmount}")
        embed.add_field(name=":dagger: Arena Wins", value=f"{wins}, {winrate}%")
        embed.add_field(name=":shield: Arena Losses", value=f"{losses}, {loserate}%")
        embed.add_field(name=":broken_heart: Arena Draws", value=f"{draws}, {drawrate}%")
        embed.add_field(name="Last 5 Results", value=f"{resultText}")
        embed.add_field(name="Last 5 Replays", value=f"{replayText}")
        embed.add_field(name=":floppy_disk: Uncache Timer", value=f"<t:{cacheExp}:R>")
        # embed.set_footer(text=f"The first timezone is {tz1String} and the second is {tz2String}.")

        if not imgErr:
            embed.set_image(url=f"attachment://{combinedIds}")

        res = {
            'embed': embed,
            'name': name,
            'matches': matches,
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'winrate': winrate,
            'loserate': loserate,
            'drawrate': drawrate,
            'latest': latestMatches,
            'replays': replayText,
            'streakType': streakType,
            'streakAmount': streakAmount
        }

        if not imgErr:
            res['image'] = combinedImg

    except Exception as e:
        # traceback.print_exc()
        logger.error(e)
        await sendErrorToManagers(e, name)

        return None

    # save to the cache
    battlesCache[roninAddr] = {"data": res, "cache": cacheExp}

    return res


# returns data on scholar's battles
async def getScholarBattles(discordId, targetId, discordName, roninAddr):
    global battlesCache

    # check caching
    if targetId in battlesCache and int(battlesCache[targetId]["cache"]) - int(time.time()) > 0:
        return battlesCache[targetId]["data"]

    # fetch data
    url = gameAPI + "/clients/" + roninAddr + "/battles?offset=0&limit=0&battle_type=0"
    jsonDat = await makeJsonRequest(url, "none")

    urlRank = gameAPI + "/leaderboard?client_id=" + roninAddr + "&offset=0&limit=0"
    jsonDatRank = await makeJsonRequest(urlRank, "none")

    # fail out if any data is missing
    if jsonDat is None or jsonDatRank is None:
        return None

    cacheExp = int(time.time()) + CACHE_TIME * 60
    res = None
    try:
        battles = jsonDat['items']

        # Arena data, mmr/rank
        player = jsonDatRank['items'][1]
        name = player["name"]
        mmr = int(player["elo"])
        rank = int(player["rank"])

        utc_time = int(datetime.datetime.now(tzutc).timestamp())
        cacheExp = utc_time + CACHE_TIME * 60

        streakType = None
        streakBroken = False
        streakAmount = 0
        axieIds = []

        wins = 0
        losses = 0
        draws = 0
        lastTime = None
        latestMatches = []
        for battle in battles:
            result = None

            if lastTime is None:
                lastTime = datetime.datetime.strptime(battle['created_at'], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=tzutc)

            # opponent ronin
            opponent = None
            pos = None
            if battle['first_client_id'] == roninAddr:
                opponent = battle['second_client_id']
                pos = 0
                if len(axieIds) == 0:
                    teamId = battle['first_team_id']
                    for axie in battle['fighters']:
                        if axie['team_id'] == teamId:
                            axieIds.append(axie['fighter_id'])
            else:
                opponent = battle['first_client_id']
                pos = 1
                if len(axieIds) == 0:
                    teamId = battle['second_team_id']
                    for axie in battle['fighters']:
                        if axie['team_id'] == teamId:
                            axieIds.append(axie['fighter_id'])

            # count draw
            if battle['winner'] == 2:
                draws += 1
                result = 'draw'
            # count win
            elif battle['winner'] == pos:
                wins += 1
                result = 'win'
            # count loss
            else:
                losses += 1
                result = 'lose'

            # streak
            if streakBroken:
                pass
            elif streakType is None:
                streakType = result
                streakAmount = 1
            elif not streakBroken and streakType == result:
                streakAmount += 1
            elif not streakBroken and streakType != result:
                streakBroken = True

            # opponent ronin
            opponent = None
            if battle['first_client_id'] == roninAddr:
                opponent = battle['second_client_id']
            else:
                opponent = battle['first_client_id']

            if len(latestMatches) < 5:
                latestMatches.append({'result': result,
                                      'replay': 'https://cdn.axieinfinity.com/game/deeplink.html?f=rpl&q={}'.format(
                                          battle['battle_uuid']), 'opponent': opponent})

        axieImages = []
        combinedImg = None
        combinedIds = None
        imgErr = False
        for axieId in axieIds:
            imgPath = './images/{}.png'.format(axieId)
            if os.path.exists(imgPath):
                axieImages.append(imgPath)
            else:
                axieUrl = 'https://storage.googleapis.com/assets.axieinfinity.com/axies/{}/axie/axie-full-transparent.png'.format(
                    axieId)
                res = saveUrlImage(axieUrl, imgPath)
                if res is None:
                    imgErr = True
                    break
                else:
                    axieImages.append(imgPath)

        if not imgErr:
            combinedIds = '{}-{}-{}.png'.format(axieIds[0], axieIds[1], axieIds[2])
            combinedImg = './images/{}-{}-{}.png'.format(axieIds[0], axieIds[1], axieIds[2])
            if not os.path.exists(combinedImg):
                res = concatImages(axieImages, combinedImg)
                if res is None:
                    imgErr = True

        matches = wins + losses + draws

        if matches == 0:
            return None

        winrate = 0
        loserate = 0
        drawrate = 0
        if matches > 0:
            winrate = round(wins / matches * 100, 2)
            loserate = round(losses / matches * 100, 2)
            drawrate = round(draws / matches * 100, 2)

        replayText = ""
        resultText = ""
        count = 1
        for match in latestMatches:
            resultText += match['result'] + '\n'
            replayText += '[Replay {}]({})\n'.format(count, match['replay'])
            count += 1

        streakText = "Current " + streakType.capitalize() + " Streak"

        cacheEast = datetime.datetime.fromtimestamp(int(cacheExp)).replace(tzinfo=tzutc).astimezone(tz1)
        cachePhil = datetime.datetime.fromtimestamp(int(cacheExp)).replace(tzinfo=tzutc).astimezone(tz2)
        cacheTxt = "`" + str(cacheEast)[:len(str(cacheEast)) - 6] + '`\n`' + str(cachePhil)[:len(str(cachePhil)) - 6] + '`\n'

        lastEast = lastTime.astimezone(tz1)
        lastPhil = lastTime.astimezone(tz2)
        lastTxt = "`" + str(lastEast)[:len(str(lastEast)) - 6] + '`\n`' + str(lastPhil)[:len(str(lastPhil)) - 6] + '`\n'

        embed = discord.Embed(title="Scholar Recent Battles", description="Recent battles for scholar " + discordName,
                              timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
        embed.add_field(name=":book: In-Game Name", value=f"{name}")
        embed.add_field(name=":clock1: Last Match Time", value=f"<t:{lastTime}:R>")
        embed.add_field(name=":anger: Arena Matches", value=f"{matches}, last ~7 days")
        embed.add_field(name=":crossed_swords: Arena MMR", value=f"{mmr}")
        embed.add_field(name=":trophy: Arena Rank", value=f"{rank}")
        embed.add_field(name=f":pencil: {streakText}", value=f"{streakAmount}")
        embed.add_field(name=":dagger: Arena Wins", value=f"{wins}, {winrate}%")
        embed.add_field(name=":shield: Arena Losses", value=f"{losses}, {loserate}%")
        embed.add_field(name=":broken_heart: Arena Draws", value=f"{draws}, {drawrate}%")
        embed.add_field(name="Last 5 Results", value=f"{resultText}")
        embed.add_field(name="Last 5 Replays", value=f"{replayText}")
        embed.add_field(name=":floppy_disk: Cached Until", value=f"<t:{cacheExp}:R>")
        # embed.set_footer(text=f"The first timezone is {tz1String} and the second is {tz2String}.")

        if not imgErr:
            embed.set_image(url=f"attachment://{combinedIds}")

        res = {
            'embed': embed,
            'matches': matches,
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'winrate': winrate,
            'loserate': loserate,
            'drawrate': drawrate,
            'latest': latestMatches,
            'replays': replayText,
            'streakType': streakType,
            'streakAmount': streakAmount
        }

        if not imgErr:
            res['image'] = combinedImg

    except Exception as e:
        # traceback.print_exc()
        logger.error(e)
        await sendErrorToManagers(e, str(targetId))

        return None

    # save to the cache
    battlesCache[targetId] = {"data": res, "cache": cacheExp}

    return res


async def getScholarExport():
    df = pd.DataFrame(columns=['ScholarID', 'ScholarName', 'Seed', 'Account', 'ScholarAddr', 'PayoutAddr', 'Share'])

    scholarsDict = await DB.getAllScholars()
    if scholarsDict["success"] is None:
        return None, None

    for scholar in scholarsDict["rows"]:
        df.loc[len(df.index)] = [scholar["discord_id"], scholar["name"], scholar["seed_num"], scholar["account_num"], scholar["scholar_addr"], scholar["payout_addr"], scholar["share"]]
    return df


# builds a summary table of all scholars
async def getScholarSummary(sort="avgslp", ascending=False, guildId=None):
    global summaryCache

    utc_time = int(datetime.datetime.now(tzutc).timestamp())
    cacheExp = utc_time + CACHE_TIME * 60
    cacheEast = datetime.datetime.fromtimestamp(int(cacheExp)).replace(tzinfo=tzutc).astimezone(tz1)

    try:
        # check caching
        if "cache" in summaryCache and int(summaryCache["cache"]) - int(time.time()) > 0:
            df = summaryCache["df"]

            # sort as desired
            if sort in ["avgslp", "slp", "adventure", "adv"]:
                df = df.sort_values(by=['SLP/Day'], ascending=ascending)
            elif sort in ["mmr", "rank", "arena", "battle"]:
                df = df.sort_values(by=['MMR'], ascending=ascending)
            elif sort == "claim":
                df = df.sort_values(by=['NextClaim'], ascending=ascending)

            df['Pos'] = np.arange(len(df))

            return df, cacheEast

        # build the data table
        df = pd.DataFrame(
            columns=['Pos', 'Scholar', 'MMR', 'ArenaRank', 'CurSLP', 'SLP/Day', 'Energy', 'PvPWins', 'PvEWins',
                     'PvESLP', 'Quest', 'NextClaim'])
        scholarsDict = await DB.getAllScholars()
        if scholarsDict["success"] is None:
            return None, None

        for scholar in scholarsDict["rows"]:
            roninKey, roninAddr = await getKeyForUser(scholar)
            if roninKey is None or roninAddr is None:
                continue
            discordId = str(scholar["discord_id"])
            res = await getPlayerDailies(discordId, discordId, "", roninKey, roninAddr, guildId)
            await asyncio.sleep(0.05)  # brief delay

            if res is not None:
                quest = False
                if res["questSlp"] == 25:
                    quest = True
                df.loc[len(df.index)] = [0, res["name"], res["mmr"], res["rank"], res["inGameSlp"], res["avgSlpPerDay"],
                                         res["energy"], res["pvpCount"], res["pveCount"], str(res["pveSlp"]) + "/50",
                                         quest, res["claimDate"].date()]

        # sort the summary table
        if sort in ["avgslp", "slp", "adventure", "adv"]:
            df = df.sort_values(by=['SLP/Day'], ascending=ascending)
        elif sort in ["mmr", "rank", "arena", "battle"]:
            df = df.sort_values(by=['MMR'], ascending=ascending)
        elif sort == "claim":
            df = df.sort_values(by=['NextClaim'], ascending=ascending)

        df['Pos'] = np.arange(len(df))

        # cache the summary data, can be re-sorted
        summaryCache["df"] = df
        summaryCache["cache"] = cacheExp

        return df, cacheEast
    except Exception as e:
        logger.error("Failed to get scholar summary")
        # traceback.print_exc()
        logger.error(e)
        await sendErrorToManagers(e, "summary")

        return None, None


async def getScholarTop10(sort="slp"):
    global summaryCache
    ascending = False

    utc_time = int(datetime.datetime.now(tzutc).timestamp())
    cacheExp = utc_time + CACHE_TIME * 60
    cacheEast = datetime.datetime.fromtimestamp(int(cacheExp)).replace(tzinfo=tzutc).astimezone(tz1)

    try:
        # check caching
        if "cache" in summaryCache and int(summaryCache["cache"]) - int(time.time()) > 0:
            df = summaryCache["df"]

            # sort as desired
            if sort in ["avgslp", "slp"]:
                # df = df.drop(columns=['MMR', 'ArenaRank', 'Energy', 'PvPWins', 'PvEWins', 'Quest', 'NextClaim'])
                df = df.sort_values(by=['SLP/Day'], ascending=ascending)
            elif sort in ["adventure", "adv"]:
                # df = df.drop(columns=['MMR', 'ArenaRank', 'CurSLP', 'SLP/Day', 'PvPWins', 'NextClaim'])
                df = df.sort_values(by=['SLP/Day'], ascending=ascending)
            elif sort in ["mmr", "rank", "battle", "arena"]:
                # df = df.drop(columns=['CurSLP', 'SLP/Day', 'PvEWins', 'PvESLP', 'Quest', 'NextClaim'])
                df = df.sort_values(by=['MMR'], ascending=ascending)

            df['Pos'] = np.arange(len(df))

            return df.head(10), cacheEast

        # build the data table
        df = pd.DataFrame(
            columns=['Pos', 'Scholar', 'MMR', 'ArenaRank', 'CurSLP', 'SLP/Day', 'Energy', 'PvPWins', 'PvEWins',
                     'PvESLP', 'Quest', 'NextClaim'])

        scholarsDict = await DB.getAllScholars()
        if scholarsDict["success"] is None:
            return None, None

        for scholar in scholarsDict["rows"]:
            roninKey, roninAddr = await getKeyForUser(scholar)
            if roninKey is None or roninAddr is None:
                continue
            discordId = str(scholar["discord_id"])
            res = await getPlayerDailies(discordId, discordId, "", roninKey, roninAddr)
            await asyncio.sleep(0.05)  # brief delay

            if res is not None:
                quest = False
                if res["questSlp"] == 25:
                    quest = True
                df.loc[len(df.index)] = [0, res["name"], res["mmr"], res["rank"], res["inGameSlp"], res["avgSlpPerDay"],
                                         res["energy"], res["pvpCount"], res["pveCount"], str(res["pveSlp"]) + "/50",
                                         quest, res["claimDate"].date()]

        df['Pos'] = np.arange(len(df))

        # cache the summary data, can be re-sorted
        summaryCache["df"] = df
        summaryCache["cache"] = cacheExp

        # sort as desired
        if sort in ["avgslp", "slp"]:
            # df = df.drop(columns=['MMR', 'ArenaRank', 'Energy', 'PvPWins', 'PvEWins', 'Quest', 'NextClaim'])
            df = df.sort_values(by=['SLP/Day'], ascending=ascending)
        elif sort in ["adventure", "adv"]:
            # df = df.drop(columns=['MMR', 'ArenaRank', 'CurSLP', 'SLP/Day', 'PvPWins', 'NextClaim'])
            df = df.sort_values(by=['SLP/Day'], ascending=ascending)
        elif sort in ["mmr", "rank", "battle", "arena"]:
            # df = df.drop(columns=['CurSLP', 'SLP/Day', 'PvEWins', 'PvESLP', 'Quest', 'NextClaim'])
            df = df.sort_values(by=['MMR'], ascending=ascending)

        df['Pos'] = np.arange(len(df))

        return df.head(10), cacheEast
    except Exception as e:
        logger.error("Failed to get scholar top 10")
        # traceback.print_exc()
        logger.error(e)
        await sendErrorToManagers(e, "top10")

        return None, None


# gets axies from a player's team
async def getPlayerAxies(discordId, discordName, roninKey, roninAddr, teamIndex=-1):
    global teamCache

    # caching
    if discordId in teamCache and teamIndex == -1:
        if int(teamCache[discordId]["cache"]) - int(time.time()) > 0:
            return teamCache[discordId]

    # auth token
    token = getPlayerToken(roninKey, roninAddr)
    if token is None:
        return None

    url = gameAPI + "/clients/" + roninAddr + "/teams?offset=0&limit=20"
    jsonDat = await makeJsonRequest(url, token)

    if jsonDat is None:
        return None

    utc_time = int(datetime.datetime.now(tzutc).timestamp())
    cacheExp = utc_time + 24 * 60 * 60 * 3  # 3 days
    try:
        ind = -1
        if teamIndex <= 0:
            ind = 0
        elif teamIndex >= len(jsonDat['items']):
            ind = len(jsonDat['items']) - 1
        else:
            ind = teamIndex
        jsonDat = jsonDat['items'][ind]

        teamName = jsonDat["name"]
        axie1 = jsonDat["members"][0]
        axie2 = jsonDat["members"][1]
        axie3 = jsonDat["members"][2]
        axieIds = [axie1["fighter_id"], axie2["fighter_id"], axie3["fighter_id"]]
        axieLevels = [axie1["level"], axie2["level"], axie3["level"]]

        axieParts = {}
        k = 0
        # request genetic data for each axie
        for axId in axieIds:
            urlParts = f"https://api.axie.technology/getgenes/{axId}/all"
            res = await makeJsonRequestWeb(urlParts)

            axieParts[axId] = {"stats": res["stats"], "class": res["class"], "parts": res["parts"], "name": res["name"],
                               "level": axieLevels[k]}
            k += 1

        avgLevel = round(float(axieLevels[0] + axieLevels[1] + axieLevels[2]) / 3.0, 1)

        embed = discord.Embed(title="Scholar Axies", description="Axies for scholar " + discordName,
                              timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
        embed.add_field(name="Scholar Name", value=f"{discordName}")
        embed.add_field(name="Team Name", value=f"{teamName}")
        embed.add_field(name="Avg Axie Level", value=f"{avgLevel}")

        mobileEmbed = discord.Embed(title="Scholar Axies", description="Axies for scholar " + discordName,
                                    timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
        mobileEmbed.add_field(name="Scholar Name", value=f"{discordName}")
        mobileEmbed.add_field(name="Team Name", value=f"{teamName}")
        mobileEmbed.add_field(name="Avg Axie Level", value=f"{avgLevel}")

        embedComps = []

        j = 1
        axieTitle = ""
        axieBody = ""
        # build the message component for each axie
        for i in axieIds:
            stats = axieParts[i]["stats"]
            axieStats = "%d HP / %d Morale / %d Speed / %d Skill\n" % (
                stats["hp"], stats["morale"], stats["speed"], stats["skill"])

            axieTitle = axieParts[i]["class"].capitalize() + " Axie " + str(j) + ": " + axieParts[i][
                "name"] + ", Level " + str(axieParts[i]["level"])
            embed.add_field(name=f"{axieTitle}", value=f"{axieStats}")
            mobileEmbed.add_field(name=f"{axieTitle}", value=f"{axieStats}")

            axie = {}
            for part in axieParts[i]["parts"]:
                if len(part["abilities"]) > 0:
                    ability = part["abilities"][0]

                    piece = "%s, %s (%s)\n" % (part["class"], part["name"], ability["name"])
                    piece += "`%d atk` / `%d def` / `%d energy`: %s\n" % (
                        ability["attack"], ability["defense"], ability["energy"], ability["description"])
                    pType = part["type"]
                    axie[pType] = piece

                    mobileEmbed.add_field(name=f"{pType} {j}", value=f"{piece}")

                else:
                    pass
            # msg += " - Picture: %s\n" % ("https://storage.googleapis.com/assets.axieinfinity.com/axies/" + str(i) + "/axie/axie-full-transparent.png")
            embedComps.append(axie)

            j += 1

        for part in ["Back", "Mouth", "Horn", "Tail"]:
            for i in range(0, 3):
                txt = embedComps[i][part]
                embed.add_field(name=f"{part} {i}", value=f"{txt}")

        axieImages = []
        combinedImg = None
        combinedIds = None
        imgErr = False
        for axieId in axieIds:
            imgPath = './images/{}.png'.format(axieId)
            if os.path.exists(imgPath):
                axieImages.append(imgPath)
            else:
                axieUrl = 'https://storage.googleapis.com/assets.axieinfinity.com/axies/{}/axie/axie-full-transparent.png'.format(axieId)
                res = saveUrlImage(axieUrl, imgPath)
                if res is None:
                    imgErr = True
                    break
                else:
                    axieImages.append(imgPath)

        if not imgErr:
            combinedIds = '{}-{}-{}.png'.format(axieIds[0], axieIds[1], axieIds[2])
            combinedImg = './images/{}-{}-{}.png'.format(axieIds[0], axieIds[1], axieIds[2])
            if not os.path.exists(combinedImg):
                res = concatImages(axieImages, combinedImg)
                if res is None:
                    imgErr = True

        if not imgErr:
            embed.set_image(url=f"attachment://{combinedIds}")
            mobileEmbed.set_image(url=f"attachment://{combinedIds}")

        # save to cache
        teamCache[discordId] = {"cache": cacheExp, "embed": embed, "mobileEmbed": mobileEmbed, "image": combinedImg}

        # logger.info(msg)

        return teamCache[discordId]
    except Exception as e:
        logger.error("Failed in getPlayerAxies")
        # traceback.print_exc()
        logger.error(e)
        await sendErrorToManagers(e, discordId)

        return None


async def nearResetAlerts(rn, forceAlert=False, alertPing=True):
    try:
        logger.info("Processing near-reset alerts")

        channel = Common.client.get_channel(Common.alertChannelId)
        msg = ""

        if not forceAlert:
            msg = "Hello %s! The %s daily reset is in 1 hour.\n\n" % (Common.programName, str(rn.date()))
        else:
            msg = "Hello %s!\n\n" % Common.programName

        count = 0

        greenCheck = ":white_check_mark:"
        redX = ":x:"

        # for each scholar
        scholarsDict = await DB.getAllScholars()
        if not scholarsDict["success"]:
            return

        for scholar in scholarsDict["rows"]:
            roninKey, roninAddr = await getKeyForUser(scholar)
            if roninKey is None or roninAddr is None:
                continue

            name = scholar["name"]
            dId = scholar["discord_id"]

            # fetch daily progress data
            res = await getPlayerDailies("", dId, name, roninKey, roninAddr)

            # configure alert messages
            if res is not None:
                alert = res["questSlp"] != 25 or res["energy"] > 0 or res["pveSlp"] < 50 or res["mmr"] < 1000
                congrats = res["pvpCount"] >= 15
                if alert or congrats:
                    # send early to avoid message size limits
                    if len(msg) >= 1600:
                        await channel.send(msg)
                        msg = ""

                    if alertPing:
                        msg += '<@' + str(dId) + '>:\n'
                    else:
                        msg += name.replace('`', '') + ":\n"

                    if res["questSlp"] != 25:
                        msg += '%s You have not completed/claimed the daily quest yet\n' % redX
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
        await channel.send(msg)
    except Exception as e:
        logger.error("Failed to process near reset alerts")
        logger.error(e)
        logger.error(traceback.format_exc())
