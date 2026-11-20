# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

ACTIVE_ROUND_STATES = ("draft", "quoting")


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    rfq_round_line_ids = fields.Many2many(
        "purchase.rfq.round.line",
        "purchase_rfq_round_line_request_line_rel",
        "request_line_id",
        "round_line_id",
        string="Quotation Round Items",
        readonly=True,
        copy=False,
    )
    rfq_round_id = fields.Many2one(
        "purchase.rfq.round",
        compute="_compute_rfq_round_id",
        string="Active Quotation Round",
        help="Rodada de cotação em aberto (rascunho ou em cotação) que "
        "contém esta linha.",
    )

    @api.depends("rfq_round_line_ids.round_id.state")
    def _compute_rfq_round_id(self):
        for line in self:
            rounds = line.rfq_round_line_ids.round_id.filtered(
                lambda r: r.state in ACTIVE_ROUND_STATES
            )
            line.rfq_round_id = rounds[:1]

    def _get_rfq_round_converted_qty(self):
        """Quantidade já em linhas de pedido não canceladas.

        Calculada das linhas de pedido, e não do ``purchased_qty``, que não
        declara dependências e fica desatualizado no cache.
        """
        self.ensure_one()
        uom = self.product_uom_id or self.product_id.uom_id
        return sum(
            pol.product_uom._compute_quantity(pol.product_qty, uom, round=False)
            for pol in self.purchase_lines
            if pol.state != "cancel"
        )
