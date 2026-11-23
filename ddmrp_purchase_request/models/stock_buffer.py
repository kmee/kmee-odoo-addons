# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from .purchase_request_line import OPEN_REQUEST_STATES


class StockBuffer(models.Model):
    _inherit = "stock.buffer"

    purchase_request_line_ids = fields.One2many(
        comodel_name="purchase.request.line",
        inverse_name="buffer_id",
        string="Purchase Request Lines",
        readonly=True,
    )
    purchase_request_count = fields.Integer(
        compute="_compute_purchase_request_qty",
        string="Purchase Requests",
    )
    purchase_request_pending_qty = fields.Float(
        compute="_compute_purchase_request_qty",
        string="Requested (pending)",
        digits="Product Unit of Measure",
        help="Quantidade em requisições de compra abertas que ainda não virou "
        "cotação nem pedido. É descontada da recomendação de reposição.",
    )

    @api.depends(
        "purchase_request_line_ids.product_qty",
        "purchase_request_line_ids.purchase_lines.product_qty",
        "purchase_request_line_ids.purchase_lines.state",
        "purchase_request_line_ids.request_state",
        "purchase_request_line_ids.cancelled",
    )
    def _compute_purchase_request_qty(self):
        for rec in self:
            lines = rec._get_open_purchase_request_lines()
            rec.purchase_request_count = len(lines.mapped("request_id"))
            rec.purchase_request_pending_qty = sum(
                line._get_buffer_pending_qty() for line in lines
            )

    def _get_open_purchase_request_lines(self):
        """Linhas de requisição abertas ligadas ao buffer.

        Ponto de extensão: módulos que tratam parte dessas linhas por outro
        caminho (por exemplo, uma rodada de cotação) podem filtrá-las aqui.
        """
        self.ensure_one()
        return self.purchase_request_line_ids.filtered(
            lambda line: not line.cancelled
            and line.request_state in OPEN_REQUEST_STATES
        )

    def _quantity_in_progress(self):
        res = super()._quantity_in_progress()
        for buffer in self:
            res[buffer.id] += sum(
                line._get_buffer_pending_qty()
                for line in buffer._get_open_purchase_request_lines()
            )
        return res

    def action_view_purchase_request(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_request.purchase_request_line_form_action"
        )
        action["domain"] = [("buffer_id", "=", self.id)]
        action["context"] = {}
        return action
