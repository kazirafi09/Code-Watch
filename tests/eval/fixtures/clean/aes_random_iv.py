import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
def encrypt(key, data):
    iv = os.urandom(16)
    c = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return iv + c.update(data) + c.finalize()
