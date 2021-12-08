import asyncio
import json
import time
from math import floor

import requests
from loguru import logger
from web3 import Web3

import AccessToken
# DONT TOUCH ANYTHING BELOW THIS LINE
import txUtils
import DB

contract, contractCall = txUtils.slp()
dev_address = '0xc381c963ec026572ea82d18dacf49a1fde4a72dc'


async def getSLP(token, address, requestType, attempts=0):
    if requestType == "POST":
        url = "https://game-api.skymavis.com/game-api/clients/" + address + "/items/1/claim"
    else:
        url = "https://game-api.skymavis.com/game-api/clients/" + address + "/items/1"
    headers = {
        'Authorization': 'Bearer ' + token,
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)',
    }
    response = requests.request(requestType, url, headers=headers)
    try:
        slp = json.loads(response.text)
        if slp['success']:
            if requestType == "POST":
                await DB.addClaimLog(address, slp["last_claimed_item_at"], slp["claimable_total"])

            return response.text
        else:
            raise Exception("success = false")

    except Exception as e:
        if attempts >= 3:
            logger.error(e)
            logger.error(response)
            logger.error(response.text)
            logger.error("Was not able to get the slp of " + address + ". Tried 3 times. Request type " + requestType)
            return None
        else:
            logger.error("Could not get the slp of " + address + " trying again #" + str(attempts) + ".")
            return await getSLP(token, address, requestType, attempts + 1)


async def ClaimSLP(key, address, data, attempt=0):
    try:
        amount = contractCall.functions.balanceOf(Web3.toChecksumAddress(address)).call()
    except Exception as e:
        logger.error(e)
        return False
    if amount != 0:
        logger.warning(f"{address} has an existing SLP balance. Please resolve before claiming.")
        return False

    signature = data['blockchain_related']['signature']['signature']
    amount = data['blockchain_related']['signature']['amount']
    timestamp = data['blockchain_related']['signature']['timestamp']
    claim_txn = contract.functions.checkpoint(
        Web3.toChecksumAddress(address),
        amount,
        timestamp,
        signature
    ).buildTransaction({
        'chainId': 2020,
        'gas': 491337,
        'gasPrice': Web3.toWei('0', 'gwei'),
        'nonce': txUtils.web3.eth.get_transaction_count(Web3.toChecksumAddress(address))
    })
    signed_txn = txUtils.web3.eth.account.sign_transaction(claim_txn, private_key=key)
    success = await txUtils.sendTx(signed_txn)
    slpClaimed = Web3.toHex(Web3.keccak(signed_txn.rawTransaction))
    if success:
        logger.success("SLP was claimed for " + address + " at tx " + slpClaimed)
        return slpClaimed
    elif attempt > 5:
        logger.error("Failed to claim scholar " + address + " retried " + str(attempt) + " times.")
        return None
    else:
        logger.warning("Failed to claim scholar " + address + " retrying #" + str(attempt))
        await asyncio.sleep(5)
        return await ClaimSLP(key, address, data, attempt + 1)


async def sendTx(key, address, amount, destination, attempt=0):
    send_txn = contract.functions.transfer(
        Web3.toChecksumAddress(destination),
        amount
    ).buildTransaction({
        'chainId': 2020,
        'gas': 491337,
        'gasPrice': Web3.toWei('0', 'gwei'),
        'nonce': txUtils.web3.eth.get_transaction_count(Web3.toChecksumAddress(address))
    })
    signed_txn = txUtils.web3.eth.account.sign_transaction(send_txn, private_key=key)
    success = await txUtils.sendTx(signed_txn)
    slpSent = Web3.toHex(Web3.keccak(signed_txn.rawTransaction))
    if success:
        logger.success(str(amount) + " slp sent to " + destination + " at tx " + slpSent)
        return slpSent
    elif attempt > 5:
        logger.error("Failed to send " + str(amount) + "slp to " + destination + " retried " + str(attempt) + " times.")
        return None
    else:
        logger.warning("Failed to send slp to " + destination + " retrying #" + str(attempt))
        await asyncio.sleep(3)
        return await sendTx(key, address, amount, destination, attempt + 1)


async def sendSLP(key, address, scholar_address, owner_address, scholar_percent, devPercent):
    try:
        amount = contractCall.functions.balanceOf(Web3.toChecksumAddress(address)).call()
    except Exception as e:
        logger.error(e)
        return None
    if not isinstance(amount, int):
        logger.error("amount is not an int")
        return None

    if amount == 0:
        logger.error(f"Tried sending SLP for {address} but there is no balance")
        return {
            "totalAmount": 0,
            "devTx": None,
            "devAmount": 0,
            "ownerTx": None,
            "ownerAmount": 0,
            "scholarTx": None,
            "scholarAmount": 0
        }

    scholar_slp = floor(amount * scholar_percent)

    if devPercent and 1 - scholar_percent > devPercent:
        dev_slp = floor(devPercent * amount)
        owner_slp = amount - (scholar_slp + dev_slp)
    else:
        dev_slp = 0
        owner_slp = amount - scholar_slp

    scholarTx = await sendTx(key, address, scholar_slp, scholar_address)
    await asyncio.sleep(3)
    ownerTx = await sendTx(key, address, owner_slp, owner_address)
    await asyncio.sleep(3)
    if devPercent:
        devTx = await sendTx(key, address, dev_slp, dev_address)
    else:
        devTx = None

    logger.success("Scholar " + address + " payout successful")
    return {
        "totalAmount": amount,
        "devTx": devTx,
        "devAmount": dev_slp,
        "ownerTx": ownerTx,
        "ownerAmount": owner_slp,
        "scholarTx": scholarTx,
        "scholarAmount": scholar_slp
    }


async def slpClaiming(key, address, scholar_address, owner_address, scholar_percent, devPercent=None):
    accessToken = AccessToken.GenerateAccessToken(key, address)
    try:
        slp_data = json.loads(await getSLP(accessToken, address, "GET"))

        # if there is a recent claim, add it to the DB
        if slp_data['last_claimed_item_at'] + 1209600 > time.time():
            await DB.addClaimLog(address, int(slp_data['last_claimed_item_at']), 0)

        # check if claim is ready
        if slp_data['last_claimed_item_at'] + 1209600 <= time.time():
            json_data = json.loads(await getSLP(accessToken, address, "POST"))
            logger.info(address + "\tclaim and update")
            claimTx = await ClaimSLP(key, address, json_data)

        # check if next claim isn't ready, but API indicates there is claimable SLP
        elif slp_data['blockchain_related']['checkpoint'] != slp_data['blockchain_related']['signature']['amount']:
            logger.info(address + "\tclaim, no update")
            claimTx = await ClaimSLP(key, address, slp_data)

        # claim isn't ready and this is normal
        else:
            claimTx = None
            if slp_data['last_claimed_item_at'] + 1209600 > time.time():
                logger.info(address + " cannot be claimed yet. Please wait " + str((slp_data['last_claimed_item_at'] + 1209600) - time.time()) + " more seconds")
                return slp_data['last_claimed_item_at'] + 1209600  # integer indicates "not ready to claim"
            elif slp_data['blockchain_related']['balance'] == 0 and slp_data['claimable_total'] == 0:
                logger.warning("No SLP Balance")
                return None  # none indicates "error"

        # claimed, process the SLP
        if not claimTx:
            return None
        else:
            sendTxs = await sendSLP(key, address, scholar_address, owner_address, scholar_percent, devPercent)
            sendTxs["claimTx"] = claimTx
            return sendTxs

    except Exception as e:
        logger.error(e)
        logger.error("Could not claim SLP")
        return None
