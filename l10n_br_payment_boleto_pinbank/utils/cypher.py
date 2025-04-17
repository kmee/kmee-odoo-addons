import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class AESCipher:
    def __init__(self, key):
        self.key = key
        self.iv = b"\0" * 16
        self.backend = default_backend()
        self.block_size = 128  # bits

    def encrypt(self, raw: str) -> bytes:
        padder = padding.PKCS7(self.block_size).padder()
        padded_data = padder.update(raw.encode()) + padder.finalize()

        cipher = Cipher(
            algorithms.AES(self.key), modes.CBC(self.iv), backend=self.backend
        )
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        return base64.b64encode(encrypted)

    def decrypt(self, enc: bytes) -> str:
        enc = base64.b64decode(enc)

        cipher = Cipher(
            algorithms.AES(self.key), modes.CBC(self.iv), backend=self.backend
        )
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(enc) + decryptor.finalize()

        unpadder = padding.PKCS7(self.block_size).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()

        return decrypted.decode("utf-8")
