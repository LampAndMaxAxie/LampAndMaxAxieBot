import json
import requests
from eth_account.messages import encode_defunct
from web3 import Web3
from loguru import logger
import traceback


def GenerateAccessToken(key, address, attempts=0):
    def getRandomMessage(attempts2=0):
        try:
            url = "https://graphql-gateway.axieinfinity.com/graphql"

            payload = '{"query":"mutation CreateRandomMessage{createRandomMessage}","variables":{}}'
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)'
            }

            response = requests.request("POST", url, headers=headers, data=payload)
            json_data = json.loads(response.text)
            return json_data['data']['createRandomMessage']
        except:
            if attempts2 > 3:
                logger.error("Could not generate AccessToken Random Message. Are the servers having issues?")
                logger.error(traceback.format_exc())
                return None
            else:
                return getRandomMessage(attempts2 + 1)

    def signRoninMessage(message, key, attempts2=0):
        try:
            mes = encode_defunct(text=message)
            ronweb3 = Web3(Web3.HTTPProvider('https://api.roninchain.com/rpc', request_kwargs={"headers": {"content-type": "application/json", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"}}))
            sig = ronweb3.eth.account.sign_message(mes, private_key=key)
            signature = sig['signature'].hex()
            return signature
        except:
            if attempts2 > 3:
                logger.error("Could not Sign Message. Are the servers having issues?")
                logger.error(traceback.format_exc())
                return None
            else:
                return signRoninMessage(message, key, attempts2 + 1)

    def CreateAccessToken(message, signature, address, attempts2=0):
        try:
            url = "https://graphql-gateway.axieinfinity.com/graphql"
            payload = '{"query":"mutation CreateAccessTokenWithSignature($input:SignatureInput!){createAccessTokenWithSignature(input:$input){newAccount,result,accessToken,__typename}}","variables":{"input":{"mainnet":"ronin","owner":"' + address + '","message":"' + message + '","signature":"' + signature + '"}}}'
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)'
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            json_data = json.loads(response.text)
            return json_data['data']['createAccessTokenWithSignature']['accessToken']
        except:
            if attempts2 > 3:
                logger.error("Could not Create Access Token. Are the servers having issues?")
                logger.error(traceback.format_exc())
                return None
            else:
                return CreateAccessToken(message, signature, address, attempts2 + 1)

    try:
        myResponse = getRandomMessage()
        mySignature = signRoninMessage(myResponse, key)
        token = CreateAccessToken(repr(myResponse).replace("\'", ""), mySignature, address)
        return token
    except:
        if attempts > 3:
            logger.error("Unable To generate Access Token. This is gernerally an internet issue or a server issue.")
            logger.error(traceback.format_exc())
            return None
        else:
            return GenerateAccessToken(key, address, attempts + 1)
