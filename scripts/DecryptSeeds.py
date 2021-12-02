from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2
from SeedStorage import *
import binascii
import getpass

# AES supports multiple key sizes: 16 (AES128), 24 (AES192), or 32 (AES256).
key_bytes = 32

# Takes as input a 32-byte key and an arbitrary-length plaintext and returns a
# pair (iv, ciphtertext). "iv" stands for initialization vector.
def encrypt(key, plaintext, iv=None):
    assert len(key) == key_bytes

    # Choose a random, 16-byte IV.
    if iv is None:
        iv = Random.new().read(AES.block_size)

    # Convert the IV to a Python integer.
    iv_int = int(binascii.hexlify(iv), 16)

    # Create a new Counter object with IV = iv_int.
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)

    # Create AES-CTR cipher.
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    # Encrypt and return IV and ciphertext.
    ciphertext = aes.encrypt(plaintext)
    return (iv, ciphertext)

# Takes as input a 32-byte key, a 16-byte IV, and a ciphertext, and outputs the
# corresponding plaintext.
def decrypt(key, iv, ciphertext):
    assert len(key) == key_bytes

    # Initialize counter for decryption. iv should be the same as the output of
    # encrypt().
    iv_int = int(binascii.hexlify(iv), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)

    # Create AES-CTR cipher.
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    # Decrypt and return the plaintext.
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
    for seed in SeedList:
        #print(f"Encrypted seed {count}: {seed}")

        try:
            res = decrypt(key, iv, seed).decode("utf8")
        except:
            print(f"Invalid decryption output detected for seed {count}, likely wrong password or corrupt IV data file.")
            count += 1
            continue

        print(f"Seed {count}: {res}")
        count += 1

print("\nDone.")

