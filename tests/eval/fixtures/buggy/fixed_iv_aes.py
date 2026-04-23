from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
IV = b"0000000000000000"
def encrypt(key, data):
    c = Cipher(algorithms.AES(key), modes.CBC(IV)).encryptor()
    return c.update(data) + c.finalize()
