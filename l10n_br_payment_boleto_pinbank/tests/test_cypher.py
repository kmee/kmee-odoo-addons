import json

from odoo.tests.common import TransactionCase

from ..utils.cypher import AESCipher
from .fixtures import (
    GENERATE_BOLETO_PAYLOAD_DECRYPTED,
    GENERATE_BOLETO_PAYLOAD_ENCRYPTED,
)


class TestPayloadEncrypt(TransactionCase):
    def setUp(self):
        super().setUp()
        secret = "1234567890123456"  # 16 bytes for AES-128
        self.cypher = AESCipher(key=secret.encode("utf-8"))

    def test_generate_boleto_payload_encrypt(self):
        """
        Test the encryption of a boleto payload.

        This test ensures that the `encrypt` method of the `cypher` object
        correctly encrypts a JSON payload. It compares the encrypted output
        with the expected encrypted payload to verify correctness.

        Assertions:
            - The encrypted JSON payload matches the expected encrypted payload.
        """

        json_payload = json.dumps(GENERATE_BOLETO_PAYLOAD_DECRYPTED, ensure_ascii=False)
        encrypted_json = self.cypher.encrypt(json_payload)
        self.assertEqual(
            encrypted_json,
            GENERATE_BOLETO_PAYLOAD_ENCRYPTED,
            "Payload not encrypted correctly",
        )

    def test_generate_boleto_payload_decrypt(self):
        """
        Test the decryption of an encrypted boleto payload.

        This test ensures that the `decrypt` method of the `cypher` object
        correctly decrypts the `GENERATE_BOLETO_PAYLOAD_ENCRYPTED` data and
        matches it with the expected `GENERATE_BOLETO_PAYLOAD_DECRYPTED` result.

        Assertions:
            - The decrypted JSON payload matches the expected decrypted payload.
        """
        decrypted_json = self.cypher.decrypt(GENERATE_BOLETO_PAYLOAD_ENCRYPTED)
        self.assertEqual(
            json.loads(decrypted_json),
            GENERATE_BOLETO_PAYLOAD_DECRYPTED,
            "Payload not decrypted correctly",
        )
