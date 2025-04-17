# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleBlanketOrderWizardConfirm(models.TransientModel):
    _name = "sale.blanket.order.wizard.confirm"
    _description = "Confirm Wizard for Sale or Blanket Order"

    sale_order_or_blanket_order = fields.Selection(
        selection=[("sale", "Sale Order"), ("blanket", "Blanket Order")],
        string="Order Type",
        required=True,
        default="sale",
    )

    def action_confirm(self):
        pass
