import json
from web3 import Web3, exceptions
import time
import concurrent.futures
from loguru import logger
import asyncio


with open("abis.json") as file:
    web3 = Web3(Web3.HTTPProvider('https://proxy.roninchain.com/free-gas-rpc', request_kwargs={"headers":{"content-type":"application/json","user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"}}))
    w3 = Web3(Web3.HTTPProvider('https://api.roninchain.com/rpc', request_kwargs={"headers":{"content-type":"application/json","user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"}}))
    abis = json.load(file)
    nonces = {}


def axie():
    axie_abi = abis['axie']
    axie_address = Web3.toChecksumAddress("0x32950db2a7164ae833121501c797d79e7b79d74c")
    axie_contract = web3.eth.contract(address=axie_address, abi=axie_abi)
    axie_contract_call = w3.eth.contract(address=axie_address, abi=axie_abi)
    return axie_contract, axie_contract_call


def slp():
    slp_abi = abis['slp']
    slp_address = Web3.toChecksumAddress("0xa8754b9fa15fc18bb59458815510e40a12cd2014")
    slp_contract = web3.eth.contract(address=slp_address, abi=slp_abi)
    slp_contract_call = w3.eth.contract(address=slp_address, abi=slp_abi)
    return slp_contract, slp_contract_call


def eth():
    eth_abi = abis['eth']
    eth_address = Web3.toChecksumAddress("0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5")
    eth_contract = web3.eth.contract(address=eth_address, abi=eth_abi)
    eth_contract_call = w3.eth.contract(address=eth_address, abi=eth_abi)
    return eth_contract, eth_contract_call


def axs():
    axs_abi = abis['axs']
    axs_address = Web3.toChecksumAddress("0x97a9107c1793bc407d6f527b77e7fff4d812bece")
    axs_contract = web3.eth.contract(address=axs_address, abi=axs_abi)
    axs_contract_call = w3.eth.contract(address=axs_address, abi=axs_abi)
    return axs_contract, axs_contract_call


def checkTxs(txs):
    while len(txs) > 0:
        data = txs.pop()
        tx = data[0]
        signed_txn = data[1]
        attempts = data[2]
        if tx is None or signed_txn is None:
            continue
        try:
            receipt = web3.eth.get_transaction_receipt(tx)
            if receipt["status"] == 1:
                print("Success:", end="\t")
                print(tx)
            else:
                raise Exception("success = false")
        except Exception as e:
            if attempts <= 3:
                print(e)
                txs.append([tx, signed_txn, attempts+1])
                success = sendTx(signed_txn)
                time.sleep(5)
                if success:
                    print("Claims to have worked. Will check again to make sure.")
                else:
                    print("Failed")
            else:
                print("could not check tx " + str(data))


async def checkTx(txHash):
    for a in range(20):
        try:
            web3.eth.get_transaction_receipt(txHash)
        except:
            return False
        #logger.info("waiting")
        await asyncio.sleep(3)
    return True


async def sendTx(signed_txn, timeout=0.025):
    tx = signed_txn.hash
    try:
        web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    except ValueError as e:
        logger.warning(e)
    tries = 0
    success = False
    while tries < 15:
        try:
            receipt = web3.eth.wait_for_transaction_receipt(tx, timeout)
            if receipt["status"] == 1:
                success = True
            break
        except (exceptions.TransactionNotFound, exceptions.TimeExhausted) as e:
            await asyncio.sleep(5 - 0.025)
            tries += 1
            #logger.info("Not found yet, waiting...")
    if success:
        if await checkTx(tx):
            #logger.info(f"Found tx hash on chain: {tx}")
            return True
    #logger.warning(f"Failed to find tx on chain: {tx}")
    return False


def getNonce(address):
    try:
        nonce = nonces[address]
        nonces[address] = nonce + 1
    except:
        nonce = web3.eth.get_transaction_count(Web3.toChecksumAddress(address))
        nonces[address] = nonce + 1
    return nonce


def sendTxThreads(txs, CONNECTIONS=100, TIMEOUT=10):
    claimTxs = []
    def sendTxn(signed_txn, timeout):
        print(signed_txn)
        attempts = 0
        while True:
            try:
                tx = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx, timeout)
                if receipt["status"] == 1:
                    print("success\t" + w3.toHex(w3.keccak(signed_txn.rawTransaction)))
                else:
                    print("fail\t" + w3.toHex(w3.keccak(signed_txn.rawTransaction)))
                break
            except Exception as e:
                if attempts >= 5:
                    break
                attempts += 1
                print(e)
        return w3.toHex(w3.keccak(signed_txn.rawTransaction)), signed_txn

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONNECTIONS) as executor:
        future_to_url = (executor.submit(sendTxn, tx, TIMEOUT) for tx in txs)
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                txHash, txData = future.result()
            except Exception as exc:
                txHash = None
                txData = str(type(exc))
                print(exc)
                print(txData)
            finally:
                claimTxs.append([txHash, txData, 0])

    if len(claimTxs) != 0:
        print("Waiting 30 seconds")
        time.sleep(30)
        print("Start Checking")
        checkTxs(claimTxs)
