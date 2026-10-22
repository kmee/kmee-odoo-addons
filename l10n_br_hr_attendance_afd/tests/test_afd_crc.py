# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes do CRC-16/KERMIT (Anexo V, item 8)."""

from odoo.tests.common import BaseCase

from ..models.afd_crc import crc16_hex, crc16_kermit, crc_confere, crc_da_linha


class TestAfdCrc(BaseCase):
    def test_vetor_oficial_da_portaria(self):
        """A própria Portaria dá o vetor: '123456789' -> 0x2189."""
        self.assertEqual(crc16_kermit("123456789"), 0x2189)
        self.assertEqual(crc16_hex("123456789"), "2189")

    def test_crc_de_bytes_e_de_texto_coincidem(self):
        self.assertEqual(crc16_kermit("123456789"), crc16_kermit(b"123456789"))

    def test_crc_confere_linha_valida(self):
        base = "000000001320260302T08:00:00-0300043461292850"
        linha = base + crc16_hex(base)
        self.assertTrue(crc_confere(linha))

    def test_crc_aceita_hexadecimal_minusculo(self):
        """Relógio que grava em minúsculas produz arquivo válido."""
        base = "000000001320260302T08:00:00-0300043461292850"
        linha = base + crc16_hex(base).lower()
        self.assertTrue(crc_confere(linha))

    def test_crc_reprova_linha_adulterada(self):
        base = "000000001320260302T08:00:00-0300043461292850"
        linha = base + crc16_hex(base)
        adulterada = linha.replace("08:00", "09:00")
        self.assertFalse(crc_confere(adulterada))

    def test_crc_da_linha_ignora_o_proprio_campo(self):
        base = "ABCDEFGH"
        linha = base + "0000"
        self.assertEqual(crc_da_linha(linha), crc16_hex(base))
