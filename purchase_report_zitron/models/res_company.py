# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import fields, models

DEFAULT_PURCHASE_REPORT_FOOTER_NOTE = Markup(
    "<p></p>"
)


class ResCompany(models.Model):
    _inherit = "res.company"

    purchase_report_footer_note = fields.Html(
        string="Purchase Order PDF Note",
        default=lambda self: DEFAULT_PURCHASE_REPORT_FOOTER_NOTE,
        help="Fixed text printed at the end of the last page of the purchase "
        "order PDF, followed by the order and project references.",
    )
