# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_sap(self):
        """SAP: planilha de lancamentos.

        A montagem da planilha fica no chassi; aqui declaramos apenas as
        colunas deste layout.
        """
        titulos = [
            "Data lancamento",
            "Conta",
            "Debito",
            "Credito",
            "Texto",
            "Documento",
            "Moeda",
        ]
        colunas = [
            "data",
            "conta",
            "debito",
            "credito",
            "historico",
            "documento",
            "moeda",
        ]
        return [
            (
                self._file_name(sufixo="Lancamentos", extensao="xlsx"),
                self._build_xlsx(titulos, colunas),
            )
        ]
