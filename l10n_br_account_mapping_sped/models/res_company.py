# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_br_sped_referential_plan_id = fields.Many2one(
        comodel_name="l10n_br.account.mapping.plan",
        string="Plano referencial da RFB",
        domain=[("sped_referential", "=", True)],
        help="Plano referencial usado por esta empresa na ECD (registro "
        "I051). Depende do regime: PJ em geral do Lucro Real usa o plano 1, "
        "do Lucro Presumido o plano 2, e assim por diante.",
    )
