import time
from loguru import logger
from math import floor
import requests
import json
from web3 import Web3, exceptions, AsyncHTTPProvider
from web3.eth import AsyncEth
import AccessToken
import asyncio

# DONT TOUCH ANYTHING BELOW THIS LINE
web3 = Web3(Web3.HTTPProvider('https://proxy.roninchain.com/free-gas-rpc'))
web3a = Web3(AsyncHTTPProvider('https://proxy.roninchain.com/free-gas-rpc'), modules={'eth': (AsyncEth,)}, middlewares=[])
w3 = Web3(Web3.HTTPProvider('https://api.roninchain.com/rpc'))
w3a = Web3(AsyncHTTPProvider('https://api.roninchain.com/rpc'), modules={'eth': (AsyncEth,)}, middlewares=[])
slp_abi = "[{\"constant\":false,\"inputs\":[{\"internalType\":\"address\",\"name\":\"_owner\",\"type\":\"address\"},{\"internalType\":\"uint256\",\"name\":\"_amount\",\"type\":\"uint256\"},{\"internalType\":\"uint256\",\"name\":\"_createdAt\",\"type\":\"uint256\"},{\"internalType\":\"bytes\",\"name\":\"_signature\",\"type\":\"bytes\"}],\"name\":\"checkpoint\",\"outputs\":[{\"internalType\":\"uint256\",\"name\":\"_balance\",\"type\":\"uint256\"}],\"payable\":false,\"stateMutability\":\"nonpayable\",\"type\":\"function\"},{\"constant\":false,\"inputs\":[{\"internalType\":\"address\",\"name\":\"_to\",\"type\":\"address\"},{\"internalType\":\"uint256\",\"name\":\"_value\",\"type\":\"uint256\"}],\"name\":\"transfer\",\"outputs\":[{\"internalType\":\"bool\",\"name\":\"_success\",\"type\":\"bool\"}],\"payable\":false,\"stateMutability\":\"nonpayable\",\"type\":\"function\"},{\"constant\":true,\"inputs\":[{\"internalType\":\"address\",\"name\":\"\",\"type\":\"address\"}],\"name\":\"balanceOf\",\"outputs\":[{\"internalType\":\"uint256\",\"name\":\"\",\"type\":\"uint256\"}],\"payable\":false,\"stateMutability\":\"view\",\"type\":\"function\"}]"
slp_address = "0xa8754b9fa15fc18bb59458815510e40a12cd2014"
slp_contract = web3.eth.contract(address=Web3.toChecksumAddress(slp_address), abi=slp_abi)
slp_contract_call = w3.eth.contract(address=Web3.toChecksumAddress(slp_address), abi=slp_abi)
dev_address = '0xa8da6b8948d011f063af3aa8b6beb417f75d1194'

async def updateSLP(token, address, attempts=0):
    url = "https://game-api.skymavis.com/game-api/clients/" + address + "/items/1/claim"
    headers = {
        'Authorization': 'Bearer ' + token,
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)',
    }
    response = requests.request("POST", url, headers=headers)
    try:
        slp = json.loads(response.text)
        if slp['success']:
            return response.text
        else:
            raise Exception ("success = false")
    except Exception as e:
        if attempts > 3:
            logger.error(e)
            logger.error("Was not able to update the slp of " + address + ". Tried 3 times. If the error persists, tell the Developers.")
            return None
        else:
            logger.warning("Could not update the slp of " + address + " trying again #" + str(attempts) + ". Nothing to be worried about.")
            return updateSLP(token, address, attempts+1)


async def getSLP(token, address, attempts=0):
    url = "https://game-api.skymavis.com/game-api/clients/" + address + "/items/1"
    headers = {
        'Authorization': 'Bearer ' + token,
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)',
    }
    response = requests.request("GET", url, headers=headers)
    try:
        slp = json.loads(response.text)
        if slp['success']:
            return response.text
        else:
            raise Exception ("success = false")
    except Exception as e:
        if attempts > 3:
            logger.error(e)
            logger.error("Was not able to get the slp of " + address + ". Tried 3 times. If the error persists, tell the Developers.")
            return None
        else:
            logger.warning("Could not get the slp of " + address + " trying again #" + str(attempts) + ". Nothing to be worried about.")
            return getSLP(token, address, attempts+1)


async def ClaimSLP(key, address, token, data, attempt=0):
    signature = data['blockchain_related']['signature']['signature']
    amount = data['blockchain_related']['signature']['amount']
    timestamp = data['blockchain_related']['signature']['timestamp']
    claim_txn = slp_contract.functions.checkpoint(
        Web3.toChecksumAddress(address),
        amount,
        timestamp,
        signature
    ).buildTransaction({
        'chainId': 2020,
        'gas': 500000,
        'gasPrice': web3.toWei('0', 'gwei'),
        'nonce': await web3a.eth.get_transaction_count(Web3.toChecksumAddress(address))
    })
    signed_txn = web3.eth.account.sign_transaction(claim_txn, private_key=key)
    tx = await web3a.eth.send_raw_transaction(signed_txn.rawTransaction)
    slpClaimed = web3.toHex(web3.keccak(signed_txn.rawTransaction))
    while True: # listen for 1 second then wait for 4 seconds repeatedly
        try:
            receipt = web3.eth.wait_for_transaction_receipt(tx, 1)
            if receipt["status"] == 1:
                success = True
            else:
                success = False
            break
        except (exceptions.TransactionNotFound, exceptions.TimeExhausted) as e:
            logger.info("Not found yet, waiting. Nothing to worry about.")
            await asyncio.sleep(4)
    if success:
        logger.success("SLP was claimed for " + address + " at tx " + slpClaimed)
        return slpClaimed
    elif attempt > 3:
        logger.error("Failed to claim scholar " + address + " retried " + str(attempt) + " times.")
        return None
    else:
        logger.warning("Failed to claim scholar " + address + " retrying #" + str(attempt))
        await asyncio.sleep(5)
        return ClaimSLP(key, address, token, data, attempt+1)


async def sendTx(key, address, token, amount, destination, attempt=0):
    send_txn = slp_contract.functions.transfer(
        Web3.toChecksumAddress(destination),
        amount
    ).buildTransaction({
        'chainId': 2020,
        'gas': 500000,
        'gasPrice': web3.toWei('0', 'gwei'),
        'nonce': await web3a.eth.get_transaction_count(Web3.toChecksumAddress(address))
    })
    signed_txn = web3.eth.account.sign_transaction(send_txn, private_key=key)
    tx = await web3a.eth.send_raw_transaction(signed_txn.rawTransaction)
    slpSent = web3.toHex(web3.keccak(signed_txn.rawTransaction))
    while True: # listen for 1 second then wait for 4 seconds repeatedly
        try:
            receipt = web3.eth.wait_for_transaction_receipt(tx, 1)
            if receipt["status"] == 1:
                success = True
            else:
                success = False
            break
        except (exceptions.TransactionNotFound, exceptions.TimeExhausted) as e:
            logger.info("Tx not found yet, waiting. Nothing to worry about.")
            await asyncio.sleep(4)
    if success:
        logger.success(str(amount) + " slp sent to " + address + " at tx " + slpSent)
        return slpSent
    elif attempt > 3:
        logger.error("Failed to send " + str(amount) + "slp to " + address + " retried " + str(attempt) + " times.")
        return None
    else:
        logger.warning("Failed to send slp to " + destination + " retrying #" + str(attempt))
        await asyncio.sleep(5)
        return sendTx(key, address, token, amount, destination, attempt + 1)


async def sendSLP(key, address, token, scholar_address, owner_address, scholar_percent, devPercent):
    try:
        amount = slp_contract_call.functions.balanceOf(Web3.toChecksumAddress(address)).call()
    except Exception as e:
        logger.error(e)
        return None
    if not isinstance(amount, int):
        logger.error("amount is not an int")
        return None
    scholar_slp = floor(amount * scholar_percent)
    if devPercent:
        dev_slp = floor(devPercent * amount)
        owner_slp = amount - (scholar_slp + dev_slp)
        devTx = await sendTx(key, address, token, dev_slp, dev_address)
        await asyncio.sleep(4)
    else:
        devTx = None
        dev_slp = 0
        owner_slp = amount - scholar_slp
    ownerTx = await sendTx(key, address, token, owner_slp, owner_address)
    await asyncio.sleep(4)
    scholarTx = await sendTx(key, address, token, scholar_slp, scholar_address)
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
        slp_data = json.loads(await getSLP(accessToken, address))
        if slp_data['blockchain_related']['balance'] != 0 or slp_data['last_claimed_item_at'] + 1209600 <= time.time():
            claim = json.loads(await updateSLP(accessToken, address))
            claimTx = await ClaimSLP(key, address, accessToken, claim)
            sendTxs = await sendSLP(key, address, accessToken, scholar_address, owner_address, scholar_percent, devPercent)
            sendTxs["claimTx"] = claimTx
            return sendTxs
        else:
            if slp_data['last_claimed_item_at'] + 1209600 > time.time():
                logger.info(address + " cannot be claimed yet. Please wait " + str((slp_data['last_claimed_item_at'] + 1209600) - time.time()) + " more seconds")
                return False # false indicates "not ready to claim"
            elif slp_data['blockchain_related']['balance'] == 0:
                logger.warning("No SLP Balance")
                return None # none indicates "error"
    except Exception as e:
        logger.error(e)
        logger.error("Could not claim SLP")
        return None
