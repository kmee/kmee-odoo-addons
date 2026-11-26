from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    has_been_invoiced_industrialization = fields.Boolean(
        string="Faturado na industrialização",
        copy=False,
        help="Marca o consumo da ordem de produção já levado a uma fatura de "
        "industrialização. Volta a ficar em aberto quando a fatura é cancelada.",
    )
    industrialization_invoice_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Linha na fatura",
        copy=False,
        ondelete="set null",
    )
    industrialization_invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Fatura",
        copy=False,
        ondelete="set null",
    )
