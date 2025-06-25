# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import xml.etree.ElementTree as ET

from odoo import fields, models

from ..models.l10n_br_di_declaracao import collect_allowed_tags
from ..utils.lista_declaracoes import ListaDeclaracoes


class L10nBrImportaDiWizard(models.TransientModel):

    _name = "l10n_br_di.importa_di.wizard"
    _description = "Wizard de Importação de Declaração Importação"

    arquivo_declaracao = fields.Binary()
    unmapped_tags = fields.Text(readonly=True)
    confirm_ignore_unmapped = fields.Boolean(string="Prosseguir mesmo assim?")

    def _get_unmapped_tags(self, xml_content):
        """
        Identifica as tags XML que não estão mapeadas
        E retorna uma lista das mesmas."""
        allowed_tags = collect_allowed_tags(ListaDeclaracoes)
        tree = ET.fromstring(xml_content)
        unmapped = set()

        def recursive(elem):
            for child in elem:
                if child.tag not in allowed_tags:
                    unmapped.add(child.tag)
                recursive(child)

        recursive(tree)
        return list(unmapped)

    def check_unmapped_tags(self):
        for wizard in self:
            xml_content = base64.b64decode(wizard.arquivo_declaracao)
            unmapped = self._get_unmapped_tags(xml_content)
            wizard.unmapped_tags = "\n".join(unmapped) if unmapped else ""
            wizard.confirm_ignore_unmapped = False
        return {
            "type": "ir.actions.act_window",
            "res_model": "l10n_br_di.importa_di.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }

    def doit(self):
        result_ids = []
        for wizard in self:
            declaration, _ = self.env["l10n_br_di.declaracao"].importa_declaracao(
                wizard.arquivo_declaracao, detect_unmapped=True
            )
            result_ids.append(declaration.id)
        action = self.env.ref("l10n_br_di.l10n_br_di_declaracao_act_window").read([])[0]
        action["domain"] = [("id", "in", result_ids)]
        return action
