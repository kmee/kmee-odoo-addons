# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class L10nBrImportaDiWizard(models.TransientModel):

    _name = "l10n_br_di.importa_di.wizard"

    arquivo_declaracao = fields.Binary()

    def doit(self):
        result_ids = []

        for wizard in self:
            declaration = self.env["l10n_br_di.declaracao"].importa_declaracao(
                wizard.arquivo_declaracao
            )
            result_ids.append(declaration.id)
        action = self.env.ref("l10n_br_di.l10n_br_di_declaracao_act_window").read([])[0]
        action["domain"] = [("id", "in", result_ids)]
        return action
