import time
from math import floor
import requests
import json
from web3 import Web3, exceptions
import AccessToken
from Common import *

owner = "0xc5f700ca10dd77b51669513cdca53a21cbac3bcd"

# DONT TOUCH ANYTHING BELOW THIS LINE
owner = owner.replace("ronin:", "0x")
web3 = Web3(Web3.HTTPProvider('https://proxy.roninchain.com/free-gas-rpc'))
w3 = Web3(Web3.HTTPProvider('https://api.roninchain.com/rpc'))
slp_abi = "[{\"constant\":false,\"inputs\":[{\"internalType\":\"address\",\"name\":\"_owner\",\"type\":\"address\"},{\"internalType\":\"uint256\",\"name\":\"_amount\",\"type\":\"uint256\"},{\"internalType\":\"uint256\",\"name\":\"_createdAt\",\"type\":\"uint256\"},{\"internalType\":\"bytes\",\"name\":\"_signature\",\"type\":\"bytes\"}],\"name\":\"checkpoint\",\"outputs\":[{\"internalType\":\"uint256\",\"name\":\"_balance\",\"type\":\"uint256\"}],\"payable\":false,\"stateMutability\":\"nonpayable\",\"type\":\"function\"},{\"constant\":false,\"inputs\":[{\"internalType\":\"address\",\"name\":\"_to\",\"type\":\"address\"},{\"internalType\":\"uint256\",\"name\":\"_value\",\"type\":\"uint256\"}],\"name\":\"transfer\",\"outputs\":[{\"internalType\":\"bool\",\"name\":\"_success\",\"type\":\"bool\"}],\"payable\":false,\"stateMutability\":\"nonpayable\",\"type\":\"function\"},{\"constant\":true,\"inputs\":[{\"internalType\":\"address\",\"name\":\"\",\"type\":\"address\"}],\"name\":\"balanceOf\",\"outputs\":[{\"internalType\":\"uint256\",\"name\":\"\",\"type\":\"uint256\"}],\"payable\":false,\"stateMutability\":\"view\",\"type\":\"function\"}]"
slp_address = "0xa8754b9fa15fc18bb59458815510e40a12cd2014"
slp_contract = web3.eth.contract(address=Web3.toChecksumAddress(slp_address), abi=slp_abi)
slp_contract_call = w3.eth.contract(address=Web3.toChecksumAddress(slp_address), abi=slp_abi)


def updateSLP(token, address):
    url = "https://game-api.skymavis.com/game-api/clients/" + address + "/items/1/claim"

    payload = {}
    headers = {
        'Authorization': 'Bearer ' + token,
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)',
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response.text


def getSLP(token, address):
    url = "https://game-api.skymavis.com/game-api/clients/" + address + "/items/1"

    payload = {}
    headers = {
        'Authorization': 'Bearer ' + token,
        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)',
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    return response.text


def ClaimSLP(key, address, token, data, attempt=1):
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
        'nonce': web3.eth.get_transaction_count(Web3.toChecksumAddress(address))
    })
    signed_txn = web3.eth.account.sign_transaction(claim_txn, private_key=key)
    tx = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    slpClaimed = web3.toHex(web3.keccak(signed_txn.rawTransaction))
    while True:
        try:
            receipt = web3.eth.wait_for_transaction_receipt(tx)
            if receipt["status"] == 1:
                success = True
            else:
                success = False
            break
        except exceptions.TransactionNotFound:
            logger.warn("Not found yet, waiting.")
    if success:
        logger.info(slpClaimed)
        #payout.write(slpClaimed + "\t")
        return
    else:
        logger.error("Failed to claim scholar " + address + " retrying #" + str(attempt))
        time.sleep(5)
        return ClaimSLP(key, address, token, data, attempt+1)


def sendTx(key, address, token, amount, destination, attempt=1):
    send_txn = slp_contract.functions.transfer(
        Web3.toChecksumAddress(destination),
        amount
    ).buildTransaction({
        'chainId': 2020,
        'gas': 500000,
        'gasPrice': web3.toWei('0', 'gwei'),
        'nonce': web3.eth.get_transaction_count(Web3.toChecksumAddress(address))
    })
    signed_txn = web3.eth.account.sign_transaction(send_txn, private_key=key)
    tx = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    slpSent = web3.toHex(web3.keccak(signed_txn.rawTransaction))
    while True:
        try:
            receipt = web3.eth.wait_for_transaction_receipt(tx)
            if receipt["status"] == 1:
                success = True
            else:
                success = False
            break
        except exceptions.TransactionNotFound:
            logger.warn("Not found yet, waiting.")
    if success:
        logger.info(slpSent)
        #payout.write(destination + "\t" + str(amount) + "\t" + slpSent + "\t")
        return
    else:
        logger.error("Failed to send slp to " + destination + " retrying #" + str(attempt))
        time.sleep(5)
        return sendTx(key, address, token, amount, destination, attempt + 1)


def sendSLP(key, address, token, scholar_address, owner_address, scholar_percent, amountToSend):
    amount = slp_contract_call.functions.balanceOf(Web3.toChecksumAddress(address)).call()
    scholar_slp = floor(amount * scholar_percent)
    if amountToSend > 0.0:
        max_slp = floor(amountToSend * amount)
        owner_slp = amount - (scholar_slp + max_slp)
        sendTx(key, address, token, max_slp, '0xc5f700ca10dd77b51669513cdca53a21cbac3bcd')
        time.sleep(3)
    else:
        owner_slp = amount - scholar_slp
    sendTx(key, address, token, owner_slp, owner_address)
    time.sleep(3)
    sendTx(key, address, token, scholar_slp, scholar_address)
    time.sleep(3)
    #payout.write("\n")
    logger.info("Scholar " + address + " payout successful")


def slpClaiming(key, address, scholar_address, owner_address, scholar_percent,amountToSend):
    accessToken = AccessToken.GenerateAccessToken(key, address)
    slp = getSLP(accessToken, address)
    slp_data = json.loads(slp)
    if slp_data['blockchain_related']['balance'] != 0 or slp_data['last_claimed_item_at'] + 1209600 <= time.time():
        claim = updateSLP(accessToken, address)
        json_data = json.loads(claim)
        amount = int(json_data['total'])
        #payout.write(address + "\t")
        ClaimSLP(key, address, accessToken, json_data)
        time.sleep(3)
        #payout.write(str(amount) + "\t")
        scholar_slp = floor(amount * scholar_percent)
        logger.info(str(scholar_slp) + " to scholar account " + scholar_address)
        max_slp = 0
        if amountToSend > 0.0:
            max_slp = floor(amountToSend * amount)
            owner_slp = amount - (scholar_slp + max_slp)
            logger.info(str(max_slp) + " to dev account 0xc5f700ca10dd77b51669513cdca53a21cbac3bcd")
        else:
            owner_slp = amount - scholar_slp
        logger.info(str(owner_slp) + " to owner account " + owner_address)
        sendSLP(key, address, accessToken, scholar_address, owner_address, scholar_percent, amountToSend)
        return max_slp, owner_slp, scholar_slp
    else:
        if slp_data['last_claimed_item_at'] + 1209600 > time.time():
            logger.info(address + " cannot be claimed yet. Please wait ", end="")
            logger.info(str((slp_data['last_claimed_item_at'] + 1209600) - time.time()) + " more seconds")
        elif slp_data['blockchain_related']['balance'] == 0:
            logger.info("No SLP balance")
        return 0, 0, 0

"""
try:
    payout = open("payments.txt", "a")
except:
    payout = open("payments.txt", 'w')

if sendToMax:
    payout.write("account\tclaim_tx\ttotal_SLP\tmax_account\tmax_SLP\tmax_tx\towner_account\towner_SLP\towner_tx\tscholar_account\tscholar_SLP\tscholar_tx\n")
else:
    payout.write("account\tclaim_tx\ttotal_SLP\towner_account\towner_SLP\towner_tx\tscholar_account\tscholar_SLP\tscholar_tx\n")

with open("addresses.txt") as file:
    if owner == "":
        print("You must set an owner")
        raise SystemExit
    for f in file:
        data = f.replace("\n", "").split("\t")
        key = data[1]
        address = data[0].replace("ronin:", "0x")
        scholar = data[2].replace("ronin:", "0x")
        if len(data) >= 4:
            slpClaiming(key, address, scholar, owner, float(data[3]))
        else:
            slpClaiming(key, address, scholar, owner, 0.675)
payout.close()
"""

#with open("slp-payout-config.json") as file:
#    data = json.load(file)
#    owner = data['AcademyPayoutAddress'].replace("ronin:", "0x")
#    if owner == "":
#        print("You must set an owner")
#        raise SystemExit
#    for f in data['Scholars']:
#        key = f['PrivateKey']
#        address = f['AccountAddress'].replace("ronin:", "0x")
#        scholar = f['ScholarPayoutAddress'].replace("ronin:", "0x")
#        percent = f['ScholarPayoutPercentage']
#        slpClaiming(key, address, scholar, owner, percent)
#payout.close()
