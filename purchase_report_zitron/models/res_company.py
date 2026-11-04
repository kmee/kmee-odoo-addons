# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import fields, models

DEFAULT_PURCHASE_REPORT_FOOTER_NOTE = Markup(
    "<p><strong>INSTRUÇÕES DE FATURAMENTO:</strong> Informar na Nota Fiscal o "
    "número desta OC, e o número do Projeto. Enviar NF e boleto para: "
    "financeiro.brasil@zitron.com; paulo.fuentealba@zitron.com; "
    "pelayo.taboada@zitron.com. "
    "<strong>PAGAMENTO:</strong> A Zitrón realiza pagamentos exclusivamente às "
    "segundas-feiras. Emitir boleto com vencimento compatível com esta "
    "programação. "
    "<strong>FORMA DE PAGAMENTO PREFERENCIAL:</strong> Depósito ou "
    "transferência bancária.</p>"
)


class ResCompany(models.Model):
    _inherit = "res.company"

    purchase_report_footer_note = fields.Html(
        string="Purchase Order PDF Note",
        default=lambda self: DEFAULT_PURCHASE_REPORT_FOOTER_NOTE,
        help="Fixed text printed at the end of the last page of the purchase "
        "order PDF, followed by the order and project references.",
    )
