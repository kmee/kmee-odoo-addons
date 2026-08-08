# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class AccountExportCommon(AccountTestInvoicingCommon):
    """Base compartilhada: empresa com CNPJ, contas com de-para e lancamentos."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company = cls.company_data["company"]
        cls.company.write(
            {"cnpj_cpf": "12.345.678/0001-95", "legal_name": "Empresa Demo LTDA"}
        )
        cls.journal = cls.company_data["default_journal_misc"]

        cls.account_debito = cls.company_data["default_account_revenue"]
        cls.account_credito = cls.company_data["default_account_expense"]
        cls.account_debito.l10n_br_export_code = "1101"
        cls.account_credito.l10n_br_export_code = "2201"

        cls.account_sem_depara = cls.env["account.account"].create(
            {
                "name": "Conta sem de-para",
                "code": cls._free_account_code(),
                "account_type": "asset_current",
                "company_id": cls.company.id,
            }
        )
        cls.move = cls._create_move("2026-08-05", 1500.0)

    @classmethod
    def _free_account_code(cls):
        """Codigo livre: o plano generico ja ocupa varios codigos altos."""
        codigo = 990000
        while cls.env["account.account"].search_count(
            [("code", "=", str(codigo)), ("company_id", "=", cls.company.id)]
        ):
            codigo += 1
        return str(codigo)

    @classmethod
    def _create_move(cls, date, amount, account_debito=None, post=True, ref="DOC123"):
        move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": date,
                "journal_id": cls.journal.id,
                "ref": ref,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": (account_debito or cls.account_debito).id,
                            "name": "Debito de teste",
                            "debit": amount,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": cls.account_credito.id,
                            "name": "Credito de teste",
                            "debit": 0.0,
                            "credit": amount,
                        },
                    ),
                ],
            }
        )
        if post:
            move.action_post()
        return move

    @classmethod
    def _create_multi_move(cls, date="2026-08-09"):
        """Lancamento de partidas multiplas (dois debitos, um credito)."""
        move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": date,
                "journal_id": cls.journal.id,
                "ref": "RATEIO",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": cls.account_debito.id,
                            "name": "Parte 1",
                            "debit": 400.0,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": cls.account_debito.id,
                            "name": "Parte 2",
                            "debit": 600.0,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": cls.account_credito.id,
                            "name": "Contrapartida",
                            "debit": 0.0,
                            "credit": 1000.0,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def _create_export(self, layout, moves=None, partial=False):
        # reusa a configuracao do layout quando ela ja existe: dois lotes do
        # mesmo destino precisam compartilhar a config, que e como o alerta de
        # reexportacao identifica a remessa anterior
        config = self.env["l10n_br.account.export.config"].search(
            [("layout", "=", layout), ("company_id", "=", self.company.id)], limit=1
        )
        if not config:
            config = self.env["l10n_br.account.export.config"].create(
                {
                    "name": f"Config {layout}",
                    "layout": layout,
                    "encoding": "cp1252",
                    "company_id": self.company.id,
                }
            )
        export = self.env["l10n_br.account.export"].create(
            {
                "company_id": self.company.id,
                "config_id": config.id,
                "date_start": "2026-08-01",
                "date_end": "2026-08-31",
                "partial_export": partial,
            }
        )
        if moves is not None:
            moves.write({"l10n_br_account_export_id": export.id})
        return export

    def _text(self, export, index=0):
        """Conteudo do arquivo gerado, ja decodificado."""
        return export.attachment_ids[index].raw.decode(export.config_id.encoding)

    def _lines(self, export, index=0):
        return [line for line in self._text(export, index).split("\n") if line]
