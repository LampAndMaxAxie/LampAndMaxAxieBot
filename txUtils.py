import traceback
import asyncio
import json
from loguru import logger
from web3 import Web3, exceptions

with open("abis.json") as file:
    w3 = Web3(Web3.HTTPProvider('https://api.roninchain.com/rpc', request_kwargs={"headers": {"content-type": "application/json", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"}}))
    abis = json.load(file)
    nonces = {}


def axie():
    axie_abi = abis['axie']
    axie_address = Web3.toChecksumAddress("0x32950db2a7164ae833121501c797d79e7b79d74c")
    axie_contract = w3.eth.contract(address=axie_address, abi=axie_abi)
    return axie_contract


def slp():
    slp_abi = abis['slp']
    slp_address = Web3.toChecksumAddress("0xa8754b9fa15fc18bb59458815510e40a12cd2014")
    slp_contract = w3.eth.contract(address=slp_address, abi=slp_abi)
    return slp_contract


def eth():
    eth_abi = abis['eth']
    eth_address = Web3.toChecksumAddress("0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5")
    eth_contract = w3.eth.contract(address=eth_address, abi=eth_abi)
    return eth_contract


def axs():
    axs_abi = abis['axs']
    axs_address = Web3.toChecksumAddress("0x97a9107c1793bc407d6f527b77e7fff4d812bece")
    axs_contract = w3.eth.contract(address=axs_address, abi=axs_abi)
    return axs_contract


def disperse():
    disperse_abi = abis['disperse']
    disperse_address = Web3.toChecksumAddress("0x14978681c5f8ce2f6b66d1f1551b0ec67405574c")
    disperse_contract = w3.eth.contract(address=disperse_address, abi=disperse_abi)
    return disperse_contract


async def checkTx(txHash, attempts=0):
    for a in range(5):
        try:
            w3.eth.get_transaction_receipt(txHash)
        except ValueError:
            if attempts >= 5:
                return False
            return await checkTx(txHash, attempts+1)
        except Exception as e:
            logger.error(e)
            logger.error(Web3.toHex(txHash))
            logger.error(traceback.format_exc())
            return False
        # logger.info("waiting")
        await asyncio.sleep(3)
    return True


async def sendTx(signed_txn, timeout=0.01):
    tx = signed_txn.hash
    try:
        try:
            w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        except ValueError as e:
            logger.warning(e)
        tries = 0
        success = False
        while tries < 15:
            try:
                transaction = w3.eth.wait_for_transaction_receipt(tx, timeout, 0.005)
                success = transaction["status"] == 1
                break
            except (exceptions.TransactionNotFound, exceptions.TimeExhausted, ValueError):
                await asyncio.sleep(10 - timeout)
                tries += 1
        if success:
            return await checkTx(tx)
        return False
    except Exception as e:
        logger.error(e)
        logger.error(Web3.toHex(tx))
        logger.error(signed_txn)
        logger.error(traceback.format_exc())
