from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto import Random
from Crypto.Protocol.KDF import PBKDF2
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

print("This script will ask you for a password followed by your seeds. Enter the seeds in the order you reference them for scholars. Press enter with no text to indicate there are no more seeds.")
print("Your seeds will be in memory for the brief duration of encryption and verification after you enter them, and then they will only be stored encrypted on disk.")
print("Make sure to run this script on a secure computer, possibly even with the internet disabled if you're worried about it.")
print("This process will overwrite your existing iv.dat and SeedStorage.py files if they exist.")
print("")

print("Note, the password field is hidden so it will not display what you type.")
password  = getpass.getpass("Password to encrypt your seeds: ").strip()
password2 = getpass.getpass("Confirm password: ").strip()

if password != password2:
    print("Passwords do not match.")
    exit()

print("\nGenerating key.\n")
key = PBKDF2(password.encode("utf8"), "axiesalt", key_bytes)

last = ""
count = 1
seeds = []
while True:
    seedIn = input(f"Input seed {count} (making sure there are no extra spaces) or enter to stop: ")
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

for i in range(0,len(seeds)):
    (iv, ciphertext) = encrypt(key, seeds[i].encode("utf8"), iv)
    encSeeds.append(ciphertext)

print("Writing IV data to file iv.dat. This file is used in the encryption process. If you lose this file or your password you will need to re-run this script to newly encrypt your seeds.")
with open("iv.dat", "wb") as f:
    f.write(iv)

print("Testing decryption on each seed to insure proper encryption.")

with open("iv.dat", "rb") as f:
    iv = f.read()

    for i in range(0,len(encSeeds)):
        out = decrypt(key, iv, encSeeds[i]).decode("utf8")
        if out == seeds[i]:
            print(f"Verified encryption of seed {i+1}.")
        else:
            print(f"Failed to verify encryption of seed {i+1}. Something is wrong with the password or IV data.")
            exit()

print("Writing encrypted seeds to SeedStorage.py file.")

with open("SeedStorage.py", "w") as f:
    f.write("SeedList = [\n")
    for i in range(0,len(encSeeds)):
        if i < len(encSeeds)-1:
            f.write(f"    {encSeeds[i]},\n")
        else:
            f.write(f"    {encSeeds[i]}\n")
    f.write("]\n\n")
    f.write("# Put Your Discord Bot Token Here\n")
    f.write("DiscordBotToken = ''\n")

print("Encrypted seeds successfully written to disk. Please enter your discord bot token at the bottom of the SeedStorage.py file.")
print("Encryption process complete!")

