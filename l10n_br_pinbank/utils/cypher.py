import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

class AESCipher:
    def __init__(self, key: bytes):
        self.bs = 16 
        self.key = key
        self.iv = b'\0' * 16

    def encrypt(self, raw: str) -> str:
        raw = self._pad(raw)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(raw.encode()) + encryptor.finalize()
        return base64.b64encode(encrypted).decode()

    def decrypt(self, enc: str) -> str:
        enc = base64.b64decode(enc)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(enc) + decryptor.finalize()
        return self._unpad(decrypted.decode("utf-8"))

    def _pad(self, s: str) -> str:
        padder = padding.PKCS7(self.bs * 8).padder()
        padded_data = padder.update(s.encode()) + padder.finalize()
        return padded_data.decode('latin1')

    def _unpad(self, s: str) -> str:
        unpadder = padding.PKCS7(self.bs * 8).unpadder()
        unpadded_data = unpadder.update(s.encode('latin1')) + unpadder.finalize()
        return unpadded_data.decode()
