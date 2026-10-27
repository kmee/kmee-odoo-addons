# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests.common import TransactionCase, tagged

from .. import utils


@tagged("post_install", "-at_install")
class TestUtils(TransactionCase):
    def test_normalize_cnpj_keeps_letters(self):
        self.assertEqual(utils.normalize_cnpj("12.abc.345/01de-35"), "12ABC34501DE35")
        self.assertEqual(utils.normalize_cnpj(None), "")
        self.assertEqual(utils.cnpj_root("12.ABC.345/01DE-35"), "12ABC345")
        self.assertEqual(utils.cnpj_root("123.456.789-09"), "")

    def test_normalize_document_number(self):
        cases = {
            "1234/1": "1234",
            "001234": "1234",
            "NF-1234/02": "1234",
            "1234": "1234",
            "": "",
            None: "",
            "000": "",
        }
        for raw, expected in cases.items():
            self.assertEqual(utils.normalize_document_number(raw), expected, raw)

    def test_normalize_digitable_line(self):
        self.assertEqual(
            utils.normalize_digitable_line("34191.09008 61207"), "341910900861207"
        )

    def test_to_date(self):
        self.assertEqual(utils.to_date("2026-10-26"), date(2026, 10, 26))
        self.assertIsNone(utils.to_date("0001-01-01"))
        self.assertIsNone(utils.to_date(date(1, 1, 1)))
        self.assertIsNone(utils.to_date("garbage"))

    def test_digitable_line_matches_the_bank_simulator(self):
        # Expected values come from brbank.simulador.dados.montar_linha_digitavel.
        cases = [
            (
                "341",
                1240.00,
                date(2026, 11, 5),
                1,
                "34190744424919575123249970267867116210000124000",
            ),
            (
                "001",
                3587.50,
                date(2026, 11, 8),
                2,
                "00190301051845772499717623887225116240000358750",
            ),
            (
                "237",
                1100.00,
                date(2026, 10, 25),
                10,
                "23795833682007080539365830098250516100000110000",
            ),
        ]
        for bank, amount, due, order, expected in cases:
            line = utils.build_digitable_line(
                bank, amount, due, "11222333000181:" + str(order)
            )
            self.assertEqual(line, expected)
