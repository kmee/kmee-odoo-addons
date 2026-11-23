# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRfqRoundLine(models.Model):
    _name = "purchase.rfq.round.line"
    _description = "Quotation Round Item"
    _order = "round_id, sequence, id"

    round_id = fields.Many2one(
        "purchase.rfq.round", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related="round_id.company_id", store=True)
    currency_id = fields.Many2one(related="round_id.currency_id")
    round_state = fields.Selection(related="round_id.state")
    product_id = fields.Many2one(
        "product.product",
        required=True,
        domain="[('purchase_ok', '=', True)]",
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="UoM",
        required=True,
        compute="_compute_product_uom_id",
        store=True,
        readonly=False,
        precompute=True,
    )
    product_qty = fields.Float(
        string="Quantity", required=True, digits="Product Unit of Measure"
    )
    request_line_ids = fields.Many2many(
        "purchase.request.line",
        "purchase_rfq_round_line_request_line_rel",
        "round_line_id",
        "request_line_id",
        string="Purchase Request Lines",
        copy=True,
    )
    reference_price = fields.Float(
        digits="Product Price",
        compute="_compute_reference_price",
        store=True,
        readonly=False,
        precompute=True,
        help="Preço de referência para o saving: último preço de compra do "
        "produto, ou o melhor preço da rodada anterior.",
    )
    reference_source = fields.Selection(
        [
            ("last_purchase", "Last purchase"),
            ("vendor_price", "Vendor price list"),
            ("previous_round", "Previous round"),
            ("manual", "Manual"),
        ],
        compute="_compute_reference_price",
        store=True,
        readonly=False,
        precompute=True,
    )
    quote_line_ids = fields.One2many(
        "purchase.order.line", "rfq_round_line_id", string="Quotes", readonly=True
    )
    quote_count = fields.Integer(compute="_compute_quote_stats", string="Answers")
    best_price_unit = fields.Float(
        compute="_compute_quote_stats", digits="Product Price", string="Best Price"
    )
    awarded_po_line_id = fields.Many2one(
        "purchase.order.line",
        string="Awarded Quote",
        copy=False,
        domain="[('rfq_round_line_id', '=', id)]",
    )
    awarded_partner_id = fields.Many2one(
        related="awarded_po_line_id.order_id.partner_id", string="Awarded Vendor"
    )
    awarded_price_unit = fields.Float(
        related="awarded_po_line_id.price_unit", string="Awarded Price"
    )
    amount_reference = fields.Monetary(compute="_compute_amounts")
    amount_awarded = fields.Monetary(compute="_compute_amounts")
    amount_saving = fields.Monetary(compute="_compute_amounts", string="Saving")

    @api.depends("product_id", "round_id.name")
    def _compute_display_name(self):
        for line in self:
            line.display_name = line.product_id.display_name or line.round_id.name

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for line in self:
            if line.product_id and (
                not line.product_uom_id
                or line.product_uom_id.category_id != line.product_id.uom_id.category_id
            ):
                line.product_uom_id = line.product_id.uom_po_id

    @api.depends("product_id", "product_uom_id")
    def _compute_reference_price(self):
        for line in self:
            if line.reference_source in ("previous_round", "manual"):
                continue
            price, source = line._get_default_reference_price()
            line.reference_price = price
            line.reference_source = source

    def _get_default_reference_price(self):
        """Último preço confirmado do produto, ou o menor da tabela de preços."""
        self.ensure_one()
        if not self.product_id:
            return 0.0, False
        last = self.env["purchase.order.line"].search(
            [
                ("product_id", "=", self.product_id.id),
                ("state", "in", ("purchase", "done")),
                (
                    "company_id",
                    "in",
                    (self.round_id.company_id or self.env.company).ids,
                ),
            ],
            order="date_order desc, id desc",
            limit=1,
        )
        uom = self.product_uom_id or self.product_id.uom_po_id
        if last:
            price = last.product_uom._compute_price(last.price_unit, uom)
            return price, "last_purchase"
        sellers = self._get_suggested_sellers()
        if sellers:
            seller = min(sellers, key=lambda s: s.price)
            seller_uom = seller.product_uom or self.product_id.uom_po_id
            return seller_uom._compute_price(seller.price, uom), ("vendor_price")
        return 0.0, False

    def _get_suggested_sellers(self):
        sellers = self.env["product.supplierinfo"]
        for line in self:
            company = line.round_id.company_id or self.env.company
            sellers |= line.product_id.seller_ids.filtered(
                lambda s, line=line, company=company: (
                    not s.company_id or s.company_id == company
                )
                and (not s.product_id or s.product_id == line.product_id)
            )
        return sellers

    def _answered_quotes(self):
        self.ensure_one()
        return self.quote_line_ids.filtered(
            lambda pol: pol.order_id.state != "cancel"
            and pol.price_unit > 0.0
            and pol.product_qty > 0.0
        )

    @api.depends("quote_line_ids.price_unit", "quote_line_ids.order_id.state")
    def _compute_quote_stats(self):
        for line in self:
            quotes = line._answered_quotes()
            line.quote_count = len(quotes)
            line.best_price_unit = min(quotes.mapped("price_unit"), default=0.0)

    @api.depends(
        "product_qty",
        "reference_price",
        "awarded_po_line_id.price_unit",
        "awarded_po_line_id.price_subtotal",
    )
    def _compute_amounts(self):
        for line in self:
            awarded = line.awarded_po_line_id
            line.amount_reference = line.reference_price * line.product_qty
            line.amount_awarded = (
                awarded.price_unit * line.product_qty if awarded else 0.0
            )
            line.amount_saving = (
                line.amount_reference - line.amount_awarded if awarded else 0.0
            )

    def _get_quote_sort_key(self, criterion):
        """Chave de ordenação das respostas; menor é melhor.

        Usa campos gravados (preço sem impostos convertido para a moeda da
        empresa e data prevista), e não o ``get_tender_best_lines`` do core,
        que recalcula campos de todas as linhas do grupo e não escala.
        Módulos podem acrescentar critérios.
        """
        if criterion == "price":
            return lambda pol: (pol._rfq_round_unit_price_cc(), pol.date_planned)
        if criterion == "date":
            return lambda pol: (pol.date_planned, pol._rfq_round_unit_price_cc())
        raise UserError(_("Unknown award criterion: %s", criterion))

    def _get_best_quote(self, criterion):
        self.ensure_one()
        quotes = self._answered_quotes()
        if not quotes:
            return quotes
        return min(quotes, key=self._get_quote_sort_key(criterion))

    def _award(self, po_line):
        """Define a resposta vencedora do item (ou limpa, se vazio)."""
        self.ensure_one()
        if po_line and po_line.rfq_round_line_id != self:
            raise UserError(_("This quote does not belong to the round item."))
        if po_line and po_line.price_unit <= 0.0:
            raise UserError(_("The vendor did not answer a price for this item."))
        self.awarded_po_line_id = po_line

    def _link_request_lines(self):
        """Liga as requisições só à linha vencedora (alocação de quantidade)."""
        allocation = self.env["purchase.request.allocation"]
        for line in self:
            winner = line.awarded_po_line_id
            if not winner:
                continue
            remaining = winner.product_uom._compute_quantity(
                winner.product_qty, line.product_uom_id
            )
            for req_line in line.request_line_ids:
                if winner in req_line.purchase_lines:
                    continue
                pending = req_line.product_qty - req_line._get_rfq_round_converted_qty()
                qty = min(pending, remaining)
                req_line.purchase_lines = [(4, winner.id)]
                if qty > 0.0:
                    allocation.create(
                        {
                            "requested_product_uom_qty": qty,
                            "product_uom_id": req_line.product_uom_id.id,
                            "purchase_request_line_id": req_line.id,
                            "purchase_line_id": winner.id,
                        }
                    )
                    remaining -= qty
            line.request_line_ids.mapped("request_id").filtered(
                lambda r: r.state == "approved"
            ).write({"state": "in_progress"})

    def _prepare_rfq_line_vals(self, vendor):
        self.ensure_one()
        return {
            "product_id": self.product_id.id,
            "product_qty": self.product_qty,
            "product_uom": self.product_uom_id.id,
            "price_unit": 0.0,
            "rfq_round_line_id": self.id,
        }
