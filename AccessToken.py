import json
import requests
from eth_account.messages import encode_defunct
from web3 import Web3


def signRoninMessage(message, key):
        mes = encode_defunct(text=message)
        ronweb3 = Web3(Web3.HTTPProvider('https://api.roninchain.com/rpc'))
        sig = ronweb3.eth.account.sign_message(mes, private_key=key)
        signature = sig['signature'].hex()
        temp = signature[-2:]
        signature = signature[:-2]
        if temp == "1c":
            signature += "01"
        elif temp == "1b":
            signature += "00"
        else:
            print("something went wrong with signRoninMessage")
        return signature


def GenerateAccessToken(key, address, attempts=1):
    def getRandomMessage():
        url = "https://axieinfinity.com/graphql-server-v2/graphql"

        payload = "{\"query\":\"mutation CreateRandomMessage {\\r\\n  createRandomMessage\\r\\n}\",\"variables\":{}}"
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        try:
            json_data = json.loads(response.text)
            return json_data['data']['createRandomMessage']
        except Exception as e:
            print(e)
            print(response)
            print(response.text)
            raise SystemExit

    def signRoninMessage(message, key):
        mes = encode_defunct(text=message)
        ronweb3 = Web3(Web3.HTTPProvider('https://api.roninchain.com/rpc'))
        sig = ronweb3.eth.account.sign_message(mes, private_key=key)
        signature = sig['signature'].hex()
        temp = signature[-2:]
        signature = signature[:-2]
        if temp == "1c":
            signature += "01"
        elif temp == "1b":
            signature += "00"
        else:
            print("something went wrong with signRoninMessage")
        return signature

    def CreateAccessToken(message, signature, address):
        url = "https://axieinfinity.com/graphql-server-v2/graphql"
        payload = "{\"query\":\"mutation CreateAccessTokenWithSignature($input: SignatureInput!)" \
                  "{\\r\\n  createAccessTokenWithSignature(input: $input)" \
                  "{\\r\\n    newAccount\\r\\n    result\\r\\n    accessToken\\r\\n    __typename\\r\\n  }" \
                  "\\r\\n}\\r\\n\",\"variables\":{\"input\":{\"mainnet\":\"ronin\",\"owner\":\"" + \
                  address + "\",\"message\":\"" + message + "\",\"signature\":\"" + signature + "\"}}}"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        try:
            json_data = json.loads(response.text)
            return json_data['data']['createAccessTokenWithSignature']['accessToken']
        except Exception as e:
            print(e)
            print(response)
            print(response.text)
            raise SystemExit

    try:
        myResponse = getRandomMessage()
        mySignature = signRoninMessage(myResponse, key)
        token = CreateAccessToken(repr(myResponse).replace("\'", ""), mySignature, address)
        return token
    except Exception as e:
        if attempts > 3:
            # TODO add a website guide for common errors
            print(e)
            print("Unable To generate Access Token. This is gernerally an internet issue or a server issue.")
            raise SystemExit
        else:
            return GenerateAccessToken(key, address, attempts+1)
