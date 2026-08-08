# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountExport(models.Model):
    _inherit = "l10n_br.account.export"

    def _generate_oracle_gl(self):
        """Oracle GL Interface: colunas no vocabulario do GL.

        A montagem da planilha fica no chassi; aqui declaramos apenas as
        colunas deste layout.
        """
        titulos = [
            "ACCOUNTING_DATE",
            "SEGMENT",
            "ENTERED_DR",
            "ENTERED_CR",
            "REFERENCE",
            "CURRENCY_CODE",
        ]
        colunas = ["data", "conta", "debito", "credito", "historico", "moeda"]
        return [
            (
                self._file_name(sufixo="GL_INTERFACE", extensao="xlsx"),
                self._build_xlsx(titulos, colunas, aba="GL_INTERFACE"),
            )
        ]
