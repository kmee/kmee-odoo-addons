# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAccountHistory(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.history = cls.env["l10n_br.account.history"].create(
            {
                "name": "Pagamento de fornecedor",
                "template": "Pagamento ref. %{DOC} de %{PARCEIRO} em %{MM}/%{AAAA}",
                "code": "0012",
            }
        )

    def test_render_substitui_variaveis(self):
        texto = self.history.render(
            date=date(2026, 8, 5),
            doc="NF 123",
            partner="Fornecedor Demo",
        )
        self.assertEqual(texto, "Pagamento ref. NF 123 de Fornecedor Demo em 08/2026")

    def test_render_variavel_sem_valor_vira_vazio(self):
        """Variavel sem dado nao pode vazar o token para o historico."""
        texto = self.history.render(date=date(2026, 8, 5))
        self.assertNotIn("%{", texto)
        self.assertIn("08/2026", texto)

    def test_render_normaliza_espacos(self):
        """A remocao de variavel vazia nao pode deixar espaco duplo."""
        history = self.env["l10n_br.account.history"].create(
            {"name": "T", "template": "A %{DOC} B"}
        )
        self.assertEqual(history.render(), "A B")

    def test_render_todas_as_datas(self):
        history = self.env["l10n_br.account.history"].create(
            {"name": "D", "template": "%{DD}/%{MM}/%{AA}/%{AAAA}"}
        )
        self.assertEqual(history.render(date=date(2026, 8, 5)), "05/08/26/2026")

    def test_render_for_move_line(self):
        """O atalho extrai data, documento e parceiro do proprio move."""
        partner = self.env["res.partner"].create({"name": "Cliente Demo"})
        journal = self.env["account.journal"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2026-08-05",
                "ref": "DOC-77",
                "journal_id": journal.id,
                "partner_id": partner.id,
            }
        )
        texto = self.env["l10n_br.account.history"].render_for_move_line(
            self.history, move
        )
        self.assertEqual(texto, "Pagamento ref. DOC-77 de Cliente Demo em 08/2026")

    def test_render_for_move_line_sem_historico(self):
        vazio = self.env["l10n_br.account.history"].render_for_move_line(
            self.env["l10n_br.account.history"], self.env["account.move"]
        )
        self.assertEqual(vazio, "")
