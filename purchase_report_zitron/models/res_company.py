# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    purchase_report_footer_note = fields.Html(
        string="Purchase Order PDF Note",
        help="Fixed text printed at the end of the last page of the purchase "
        "order PDF, followed by the order and project references. Empty by "
        "default: configure it per company.",
    )
