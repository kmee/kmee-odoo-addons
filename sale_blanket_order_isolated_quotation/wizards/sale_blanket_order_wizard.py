# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BlanketOrderWizard(models.TransientModel):
    _inherit = "sale.blanket.order.wizard"

    def _prepare_so_line_vals(self, line):
        vals = super()._prepare_so_line_vals(line)
        vals["discount"] = line.discount
        return vals


class BlanketOrderWizardLine(models.TransientModel):
    _inherit = "sale.blanket.order.wizard.line"

    discount = fields.Float(digits="Discount")
