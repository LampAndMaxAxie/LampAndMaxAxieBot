import binascii
import getpass

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util import Counter

# check for existing discord bot token
try:
    import SeedStorage
    discordToken = SeedStorage.DiscordBotToken
except ImportError:
    discordToken = None
    pass

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


print("This script will ask you for a password followed by your seeds. Enter the seeds in the order you reference them for scholars. Press enter with no text to indicate there are no more seeds.")
print("Your seeds will be in memory for the brief duration of encryption and verification after you enter them, and then they will only be stored encrypted on disk.")
print("Make sure to run this script on a secure computer, possibly even with the internet disabled if you're worried about it.")
print("This process will overwrite your existing iv.dat and SeedStorage.py files if they exist.")
print("")

print("Note, the password field is hidden so it will not display what you type.")
password = getpass.getpass("Password to encrypt your seeds: ").strip()
password2 = getpass.getpass("Confirm password: ").strip()

# check that password entry matches
if password != password2:
    print("Passwords do not match.")
    exit()

# produce 32-bit key with PBKDF2 standard
print("\nGenerating key.\n")
key = PBKDF2(password.encode("utf8"), "axiesalt", key_bytes)

# read in the seeds one by one
last = ""
count = 1
seeds = []
print("When you've entered your last seed phrase, press enter on a blank input to continue. Each line should be 12 words separated by a single space.\n")
while True:
    seedIn = input(f"Input seed phrase {count}: ")
    seedIn = seedIn.strip()

    if seedIn == "":
        print("\nDetected blank input, moving on to seed encryption.\n")
        break
    seeds.append(seedIn)
    count += 1
    last

# generate IV data
iv = Random.new().read(AES.block_size)
encSeeds = []

# encrypt the seeds one by one
for i in range(0, len(seeds)):
    (iv, ciphertext) = encrypt(key, seeds[i].encode("utf8"), iv)
    encSeeds.append(ciphertext)

# save the IV data
print("Writing IV data to file iv.dat. This file is used in the encryption process. If you lose this file or your password you will need to re-run this script to newly encrypt your seeds.")
with open("iv.dat", "wb") as f:
    f.write(iv)

# verify that encrypted data is correct
print("Testing decryption on each seed to insure proper encryption.")
with open("iv.dat", "rb") as f:
    iv = f.read()

    for i in range(0, len(encSeeds)):
        out = decrypt(key, iv, encSeeds[i]).decode("utf8")
        if out == seeds[i]:
            print(f"Verified encryption of seed {i + 1}.")
        else:
            print(f"Failed to verify encryption of seed {i + 1}. Something is wrong with the password or IV data.")
            exit()

# save encrypted seeds to disk
print("Writing encrypted seeds to SeedStorage.py file.")
with open("SeedStorage.py", "w") as f:
    f.write("SeedList = [\n")
    for i in range(0, len(encSeeds)):
        if i < len(encSeeds) - 1:
            f.write(f"    {encSeeds[i]},\n")
        else:
            f.write(f"    {encSeeds[i]}\n")
    f.write("]\n\n")
    f.write("# Put Your Discord Bot Token Here\n")
    
    if discordToken is None:
        f.write("DiscordBotToken = ''\n")
    else:
        f.write(f"DiscordBotToken = '{discordToken}'\n")

print("Encrypted seeds successfully written to disk. Please enter your discord bot token at the bottom of the SeedStorage.py file.")
print("Encryption process complete!")
