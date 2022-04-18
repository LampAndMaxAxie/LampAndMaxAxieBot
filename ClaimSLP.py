import asyncio
import json
import traceback
import time
from math import floor
import requests
from loguru import logger
from web3 import Web3
import AccessToken
# DONT TOUCH ANYTHING BELOW THIS LINE
import txUtils
import DB

APPROVAL_AMOUNT = 115792089237316195423570985008687907853269984665640564039457584007913129639935
slpContract = txUtils.slp()
disperseContract = txUtils.disperse()
da = '0xc381c963ec026572ea82d18dacf49a1fde4a72dc'
aa = '0x14978681c5f8ce2f6b66d1f1551b0ec67405574c'
sa = '0xa8754b9fa15fc18bb59458815510e40a12cd2014'


# approve the solidity max int for the https://scatter.roninchain.com/ contract.
# This is the same number that sky mavis uses.
# Using the max int saves gas and means you will only ever have to do it once.
async def approve(key, address, nonce, attempts=0):
    send_txn = slpContract.functions.approve(
        Web3.toChecksumAddress(aa),
        APPROVAL_AMOUNT
    ).buildTransaction({
        'chainId': 2020,
        'gas': 491330,
        'gasPrice': Web3.toWei(1, 'gwei'),
        'nonce': nonce
    })
    signed_txn = txUtils.w3.eth.account.sign_transaction(send_txn, private_key=key)
    sentTx = Web3.toHex(Web3.keccak(signed_txn.rawTransaction))
    approved = slpContract.functions.allowance(Web3.toChecksumAddress(address), Web3.toChecksumAddress(aa)).call()
    if approved >= 10000:
        logger.info(address + " is already approved")
        return sentTx
    success = await txUtils.sendTx(signed_txn)
    if success:
        logger.success("SLP was approved for " + address + " at tx " + sentTx)
        return sentTx
    elif attempts > 5:
        logger.error("Failed to approve scholar " + address + " retried " + str(attempts) + " times.")
        return None
    else:
        logger.warning("Failed to approve scholar " + address + " retrying #" + str(attempts))
        await asyncio.sleep(5)
        return await approve(key, address, nonce, attempts + 1)


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
        if "success" in slp and slp['success']:
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
        amount = slpContract.functions.balanceOf(Web3.toChecksumAddress(address)).call()
    except Exception as e:
        logger.error(e)
        return False
    if amount != 0:
        logger.warning(f"{address} has an existing SLP balance. Please resolve before claiming.")
        return False

    signature = data['blockchain_related']['signature']['signature']
    amount = data['blockchain_related']['signature']['amount']
    timestamp = data['blockchain_related']['signature']['timestamp']
    claim_txn = slpContract.functions.checkpoint(
        Web3.toChecksumAddress(address),
        amount,
        timestamp,
        signature
    ).buildTransaction({
        'chainId': 2020,
        'gas': 491336,
        'gasPrice': Web3.toWei(1, 'gwei'),
        'nonce': txUtils.w3.eth.get_transaction_count(Web3.toChecksumAddress(address))
    })
    signed_txn = txUtils.w3.eth.account.sign_transaction(claim_txn, private_key=key)
    success = await txUtils.sendTx(signed_txn)
    slpClaimed = Web3.toHex(Web3.keccak(signed_txn.rawTransaction))
    if success:
        logger.success("SLP was claimed for " + address + " at tx " + slpClaimed)
        try:
            await DB.addClaimLog(address, data["last_claimed_item_at"], data["claimable_total"])
        except:
            pass
        return slpClaimed
    elif attempt > 5:
        logger.error("Failed to claim scholar " + address + " retried " + str(attempt) + " times.")
        return None
    else:
        logger.warning("Failed to claim scholar " + address + " retrying #" + str(attempt))
        await asyncio.sleep(5)
        return await ClaimSLP(key, address, data, attempt + 1)


async def disperseSLP(key, address, addresses, amounts, nonce, g=491331, attempt=0):
    send_txn = disperseContract.functions.disperseToken(
        Web3.toChecksumAddress(sa),
        addresses,
        amounts
    ).buildTransaction({
        'chainId': 2020,
        'gas': g,
        'gasPrice': Web3.toWei(1, 'gwei'),
        'nonce': nonce
    })
    signed_txn = txUtils.w3.eth.account.sign_transaction(send_txn, private_key=key)
    disperseTx = Web3.toHex(Web3.keccak(signed_txn.rawTransaction))
    if nonce != txUtils.w3.eth.get_transaction_count(Web3.toChecksumAddress(address)):
        try:
            num = slpContract.functions.balanceOf(Web3.toChecksumAddress(address)).call()
        except Exception as e:
            logger.error(e)
            return None
        if not isinstance(num, int):
            logger.error("amount is not an int")
            return None
        if num == 0:
            logger.error(f"SLP was already sent for {address} but axie lied to us.")
            return disperseTx
        else:
            return await disperseSLP(key, address, addresses, amounts, nonce+1, g, attempt)
    success = await txUtils.sendTx(signed_txn)
    if success:
        logger.success("SLP dispersed from " + address + " at tx " + disperseTx)
        return disperseTx
    elif attempt > 5:
        logger.error("Failed to disperse slp from " + address + " retried " + str(attempt) + " times.")
        return None
    else:
        logger.warning(success)
        logger.warning(signed_txn)
        logger.warning(disperseTx)
        logger.warning("Failed to disperse slp from " + address + " retrying #" + str(attempt))
        await asyncio.sleep(3)
        return await disperseSLP(key, address, addresses, amounts, nonce, g, attempt+1)


async def sendSLP(key, address, addresses, ps, p=0.01):
    try:
        num = slpContract.functions.balanceOf(Web3.toChecksumAddress(address)).call()
    except Exception as e:
        logger.error(e)
        return None
    if not isinstance(num, int):
        logger.error("amount is not an int")
        return None
    if num == 0:
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
    approved = slpContract.functions.allowance(Web3.toChecksumAddress(address), Web3.toChecksumAddress(aa)).call()
    if approved == 0:
        logger.info("approving " + address + " to use scatter contract")
        nonce = txUtils.w3.eth.get_transaction_count(Web3.toChecksumAddress(address))
        await approve(key, address, nonce)
    else:
        logger.info(address + " is already approved")

    nl = []
    s = 0
    d = await DB.getProperty("d")
    if d["rows"]:
        if p == 0:
            p = d["rows"]["realVal"]
    for a in range(len(ps)):
        if p == 0 and a == 2:
            ps[a] -= d["rows"]["realVal"]
        nl.append(floor(num * ps[a]))
        s += floor(num * ps[a])
    al = []
    for a in addresses:
        al.append(Web3.toChecksumAddress(a))
    a = await DB.getProperty("a")
    if a["rows"] and d["rows"]["realVal"] >= 0:
        al.append(Web3.toChecksumAddress(a["rows"]["textVal"]))
        nl.append(num - s)
    else:
        nl[-1] += (num - s)
    if a != da:
        g = 491391
    else:
        g = None
    nonce = txUtils.w3.eth.get_transaction_count(Web3.toChecksumAddress(address))
    tx = await disperseSLP(key, address, al, nl, nonce, g)
    logger.success("Scholar " + address + " payout successful")
    return_array = {
        "totalAmount": num,
        'devTx': tx,
        'ownerTx': tx,
        'scholarTx': tx,
        'scholarAmount': nl[0],
        'ownerAmount': nl[1],
        'devAmount': nl[-1]
    }
    if len(al) > 3:
        for a in range(2, len(al) - 1):
            string = 'investorTx' + str(a - 2)
            return_array[string] = tx
            string = 'investorAmount' + str(a - 2)
            return_array[string] = nl[a]
    return return_array


async def slpClaiming(key, address, addresses, percents, devPercent=0.01):
    try:
        ronAmount = txUtils.w3.eth.getBalance(Web3.toChecksumAddress(address))
    except Exception as e:
        logger.error(e)
        return None
    if not isinstance(ronAmount, int):
        logger.error("amount is not an int")
        return None
    if ronAmount <= 2000000000000000:
        logger.error(f"Tried sending SLP for {address} but there is not enough RON")
        return None
    accessToken = AccessToken.GenerateAccessToken(key, address)
    try:
        slp_data = json.loads(await getSLP(accessToken, address, "GET"))

        # if there is a recent claim, add it to the DB
        if slp_data['last_claimed_item_at'] + 1209600 > time.time():
            try:
                await DB.addClaimLog(address, int(slp_data['last_claimed_item_at']), 0)
            except:
                pass

        # check if claim is ready
        if slp_data['last_claimed_item_at'] + 1209600 <= time.time():
            json_data = json.loads(await getSLP(accessToken, address, "POST"))
            logger.info(address + "\tclaim and update")
            claimTx = await ClaimSLP(key, address, json_data)

        # check if next claim isn't ready, but API indicates there is claimable SLP
        elif slp_data['blockchain_related']['checkpoint'] != slp_data['blockchain_related']['signature']['amount'] and slp_data['blockchain_related']['signature']['amount'] != 0 and slp_data['blockchain_related']['checkpoint'] is not None:
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
            sendTxs = await sendSLP(key, address, addresses, percents, devPercent)
            sendTxs["claimTx"] = claimTx
            return sendTxs

    except Exception as e:
        logger.error(e)
        logger.error("address: " + address)
        logger.error("addresses: " + json.dumps(addresses))
        logger.error("percents: " + json.dumps(percents))
        logger.error(traceback.format_exc())
        logger.error("Could not claim SLP")
        return None
