from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    nfe40_med = fields.Many2one(
        comodel_name="nfe.40.med",
        string="Grupo de Medicamento",
    )
