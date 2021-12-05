import binascii
import getpass

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util import Counter

import SeedStorage

# Encryption methodology adopted from https://stackoverflow.com/a/44662262

# 32 bit keys => AES256 encryption
key_bytes = 32


# 32 bit key, binary plaintext string to encrypt, and IV binary string
def encrypt(key, plaintext, iv=None):
    assert len(key) == key_bytes

    # create random IV if one not provided
    if iv is None:
        iv = Random.new().read(AES.block_size)

    # convert IV to integer
    iv_int = int(binascii.hexlify(iv), 16)

    # create counter using the IV
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)

    # create cipher object
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    # encrypt the string and return the IV/ciphertext
    ciphertext = aes.encrypt(plaintext)
    return iv, ciphertext


# 32 bit key, IV binary string, and ciphertext to decrypt
def decrypt(key, iv, ciphertext):
    assert len(key) == key_bytes

    # convert IV to integer and create counter using the IV
    iv_int = int(binascii.hexlify(iv), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)

    # create cipher object
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    # decrypt ciphertext and return the decrypted binary string
    plaintext = aes.decrypt(ciphertext)
    return plaintext


print("You should only use this script if you are trying to decrypt your encrypted seeds to recover them from the SeedStorage. This will require your password and the original IV data file.")
print("If successful, it will print your seed phrases in plaintext to the screen for your recovery. Make sure your computer is secure, possible disconnected from the internet, before doing this.\n")

print("Note, the password field is hidden so it will not display what you type.")
password = getpass.getpass().strip()

print("\nGenerating key.\n")
key = PBKDF2(password, "axiesalt", key_bytes)

with open("iv.dat", "rb") as f:
    iv = f.read()

    count = 1
    for seed in SeedStorage.SeedList:
        # print(f"Encrypted seed {count}: {seed}")

        try:
            res = decrypt(key, iv, seed).decode("utf8")
        except:
            print(f"Invalid decryption output detected for seed {count}, likely wrong password or corrupt IV data file.")
            count += 1
            continue

        print(f"Seed {count}: {res}")
        count += 1

print("\nDone.")
