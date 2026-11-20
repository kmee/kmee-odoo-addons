# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    rfq_approved = fields.Boolean(
        string="Approved Vendor",
        help="Fornecedor homologado para este produto (especificação técnica "
        "aprovada). Rodadas que exigem homologação só pontuam fornecedores "
        "homologados.",
    )
    rfq_approval_date = fields.Date(string="Approval Date")
    rfq_approval_note = fields.Char(string="Approval Note")
