# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests import TransactionCase, tagged

from ..models import format_helper as fh


@tagged("post_install", "-at_install")
class TestFormatHelper(TransactionCase):
    """Os helpers sao funcoes puras: testados sem ORM e sem arquivo."""

    def test_pad_alinha_e_preenche(self):
        self.assertEqual(fh.pad("AB", 5), "AB   ")
        self.assertEqual(fh.pad("AB", 5, align=fh.ALIGN_RIGHT), "   AB")
        self.assertEqual(fh.pad("AB", 5, align=fh.ALIGN_RIGHT, fill="0"), "000AB")

    def test_pad_trunca_em_vez_de_estourar(self):
        """Campo maior que o previsto desloca todo o resto do registro."""
        self.assertEqual(fh.pad("ABCDEFG", 4), "ABCD")
        self.assertEqual(len(fh.pad("ABCDEFG", 4)), 4)

    def test_zero_pad(self):
        self.assertEqual(fh.zero_pad(42, 6), "000042")
        self.assertEqual(fh.zero_pad("", 3), "000")

    def test_format_amount_virgula_sem_milhar(self):
        self.assertEqual(fh.format_amount(1234.5), "1234,50")
        self.assertEqual(fh.format_amount(29.9), "29,90")
        self.assertEqual(fh.format_amount(0), "0,00")

    def test_format_amount_ponto_e_milhar(self):
        self.assertEqual(fh.format_amount(1234.5, decimal_sep="."), "1234.50")
        self.assertEqual(
            fh.format_amount(1234.5, decimal_sep=",", thousands_sep="."), "1.234,50"
        )

    def test_format_amount_sempre_positivo(self):
        """O lado (debito ou credito) e indicado por campo, nunca por sinal."""
        self.assertEqual(fh.format_amount(-50.0), "50,00")

    def test_amount_cents(self):
        self.assertEqual(fh.amount_cents(29.9), "2990")
        self.assertEqual(fh.amount_cents(29.9, 10), "0000002990")
        self.assertEqual(fh.amount_cents(0.1), "10")

    def test_format_date(self):
        self.assertEqual(fh.format_date(date(2026, 8, 1)), "01/08/2026")
        self.assertEqual(fh.format_date(date(2026, 8, 1), "%Y%m%d"), "20260801")
        self.assertEqual(fh.format_date(False), "")

    def test_only_digits(self):
        self.assertEqual(fh.only_digits("12.345.678/0001-95"), "12345678000195")
        self.assertEqual(fh.only_digits(None), "")

    def test_clean_text_remove_quebra_e_separador(self):
        """Quebra de linha parte o registro; o separador cria campo fantasma."""
        self.assertEqual(fh.clean_text("Nota 1\nParcela 2"), "Nota 1 Parcela 2")
        self.assertEqual(fh.clean_text("Nota|1", sep="|"), "Nota 1")
        self.assertEqual(fh.clean_text("abcdef", 3), "abc")

    def test_join_delimited(self):
        self.assertEqual(fh.join_delimited(["a", "b"], ";"), "a;b")
        self.assertEqual(
            fh.join_delimited(["a", "b"], "|", leading=True, trailing=True), "|a|b|"
        )
        self.assertEqual(fh.join_delimited(["a", "b"], ",", wrap='"'), '"a","b"')
