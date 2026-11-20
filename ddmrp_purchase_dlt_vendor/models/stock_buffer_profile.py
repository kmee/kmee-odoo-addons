# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockBufferProfile(models.Model):
    _inherit = "stock.buffer.profile"

    dlt_vendor_policy = fields.Selection(
        [
            ("first", "First vendor of the list"),
            ("worst_approved", "Longest lead time among approved vendors"),
            ("worst", "Longest lead time among all vendors"),
        ],
        string="Vendor for DLT",
        default="first",
        required=True,
        help="De qual fornecedor sai o prazo (DLT) de item comprado.\n"
        "Primeiro da lista: padrão do ddmrp (sequência, quantidade mínima, "
        "preço).\n"
        "Pior prazo entre homologados: protege o buffer quando a rodada de "
        "cotação pode escolher qualquer fornecedor homologado; sem homologado, "
        "usa todos.\n"
        "Pior prazo entre todos: o mais conservador.",
    )
