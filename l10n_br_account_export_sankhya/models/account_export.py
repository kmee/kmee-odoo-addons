# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_sankhya(self):
        """Sankhya: lote contabil em planilha.

        A montagem da planilha fica no chassi; aqui declaramos apenas as
        colunas deste layout.
        """
        titulos = ["Data", "Conta", "Debito", "Credito", "Historico", "Documento"]
        colunas = ["data", "conta", "debito", "credito", "historico", "documento"]
        return [
            (
                self._file_name(sufixo="LoteContabil", extensao="xlsx"),
                self._build_xlsx(titulos, colunas),
            )
        ]
