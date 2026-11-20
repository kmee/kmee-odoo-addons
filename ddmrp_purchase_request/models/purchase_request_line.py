# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

# Estados da requisição em que a quantidade ainda vai virar compra.
OPEN_REQUEST_STATES = ("draft", "to_approve", "approved", "in_progress")


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    buffer_id = fields.Many2one(
        comodel_name="stock.buffer",
        string="Buffer",
        index=True,
        copy=False,
        readonly=True,
        ondelete="set null",
        help="Buffer DDMRP que gerou esta linha de requisição.",
    )
    buffer_pending_qty = fields.Float(
        string="Pending for Buffer",
        compute="_compute_buffer_pending_qty",
        digits="Product Unit of Measure",
        help="Quantidade da linha, na unidade do buffer, que ainda não virou "
        "linha de cotação ou pedido de compra.",
    )

    @api.depends(
        "product_qty",
        "product_uom_id",
        "purchase_lines.product_qty",
        "purchase_lines.state",
        "cancelled",
        "request_state",
        "buffer_id.product_uom",
    )
    def _compute_buffer_pending_qty(self):
        for line in self:
            line.buffer_pending_qty = line._get_buffer_pending_qty()

    def _get_converted_qty(self):
        """Quantidade já em linhas de cotação ou pedido não canceladas.

        Calculada das linhas de pedido, e não do ``purchased_qty`` do
        ``purchase_request``: aquele campo não declara dependências e fica
        desatualizado no cache dentro da mesma transação.
        """
        self.ensure_one()
        uom = self.product_uom_id or self.product_id.uom_id
        return sum(
            po_line.product_uom._compute_quantity(po_line.product_qty, uom, round=False)
            for po_line in self.purchase_lines
            if po_line.state != "cancel"
        )

    def _get_buffer_pending_qty(self):
        """Quantidade ainda não convertida em compra, na UdM do buffer.

        A parte já convertida em linha de pedido não entra: rascunhos são
        contados pelo próprio buffer (RFQ em andamento) e pedidos confirmados
        entram na posição líquida pelos movimentos previstos.
        """
        self.ensure_one()
        if (
            not self.buffer_id
            or self.cancelled
            or self.request_state not in OPEN_REQUEST_STATES
        ):
            return 0.0
        pending = self.product_qty - self._get_converted_qty()
        if pending <= 0.0:
            return 0.0
        uom = self.product_uom_id or self.product_id.uom_id
        return uom._compute_quantity(pending, self.buffer_id.product_uom, round=False)
