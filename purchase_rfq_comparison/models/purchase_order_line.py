# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    rfq_payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Answered Payment Terms",
        compute="_compute_rfq_payment_term_id",
        store=True,
        readonly=False,
        help="Condição de pagamento respondida pelo fornecedor para o item. "
        "Padrão: a condição do pedido.",
    )
    rfq_validity_date = fields.Date(string="Quote Valid Until")
    rfq_min_qty = fields.Float(
        string="Vendor Minimum Qty", digits="Product Unit of Measure"
    )
    rfq_spec_approved = fields.Boolean(
        string="Specification OK",
        compute="_compute_rfq_vendor_approved",
        store=True,
        readonly=False,
        help="O item ofertado atende à especificação técnica. Padrão: o "
        "fornecedor é homologado para o produto.",
    )
    rfq_vendor_approved = fields.Boolean(
        string="Approved Vendor",
        compute="_compute_rfq_vendor_approved",
        store=True,
    )
    rfq_payment_days = fields.Float(
        string="Avg. Payment Days",
        aggregator="avg",
        compute="_compute_rfq_financials",
        store=True,
        digits=(16, 1),
    )
    rfq_present_value = fields.Monetary(
        string="Present Value",
        compute="_compute_rfq_financials",
        store=True,
        currency_field="currency_id",
        help="Total com impostos trazido a valor presente pela condição de "
        "pagamento respondida e pela taxa mensal da rodada.",
    )
    rfq_lead_days = fields.Integer(
        string="Lead Time (days)",
        compute="_compute_rfq_lead_days",
        store=True,
        aggregator="min",
    )
    rfq_min_qty_ok = fields.Boolean(
        string="Min. Qty OK", compute="_compute_rfq_min_qty_ok", store=True
    )
    rfq_score = fields.Float(
        string="Score",
        digits=(16, 1),
        aggregator="max",
        readonly=True,
        copy=False,
        help="Pontuação de 0 a 100 da resposta dentro do item da rodada.",
    )
    rfq_eligible = fields.Boolean(string="Eligible", readonly=True, copy=False)

    @api.depends("order_id.payment_term_id")
    def _compute_rfq_payment_term_id(self):
        for line in self:
            if not line.rfq_payment_term_id:
                line.rfq_payment_term_id = line.order_id.payment_term_id

    @api.depends("product_id", "partner_id")
    def _compute_rfq_vendor_approved(self):
        for line in self:
            vendors = line.partner_id | line.partner_id.commercial_partner_id
            approved = any(
                seller.rfq_approved
                and seller.partner_id in vendors
                and (not seller.product_id or seller.product_id == line.product_id)
                for seller in line.product_id.seller_ids
            )
            line.rfq_vendor_approved = approved
            line.rfq_spec_approved = approved

    @api.depends("date_planned", "order_id.date_order")
    def _compute_rfq_lead_days(self):
        for line in self:
            if line.date_planned and line.order_id.date_order:
                line.rfq_lead_days = max(
                    (line.date_planned.date() - line.order_id.date_order.date()).days,
                    0,
                )
            else:
                line.rfq_lead_days = 0

    @api.depends("rfq_min_qty", "product_qty")
    def _compute_rfq_min_qty_ok(self):
        for line in self:
            line.rfq_min_qty_ok = line.product_qty >= line.rfq_min_qty

    @api.depends(
        "price_total",
        "rfq_payment_term_id",
        "order_id.date_order",
        "rfq_round_line_id.round_id.pv_monthly_rate",
    )
    def _compute_rfq_financials(self):
        for line in self:
            days, present = line._rfq_payment_schedule_value()
            line.rfq_payment_days = days
            line.rfq_present_value = present

    def _rfq_payment_schedule_value(self):
        """Prazo médio ponderado (dias) e valor presente do total da linha."""
        self.ensure_one()
        total = self.price_total
        term = self.rfq_payment_term_id
        date_ref = (self.order_id.date_order or fields.Datetime.now()).date()
        if not total or not term:
            return 0.0, total
        company = self.order_id.company_id or self.env.company
        terms = term._compute_terms(
            date_ref=date_ref,
            currency=self.currency_id or company.currency_id,
            company=company,
            tax_amount=0.0,
            tax_amount_currency=0.0,
            sign=1,
            untaxed_amount=total,
            untaxed_amount_currency=total,
        )
        rate = (self.rfq_round_line_id.round_id.pv_monthly_rate or 0.0) / 100.0
        weighted, present = 0.0, 0.0
        for item in terms["line_ids"]:
            amount = item["foreign_amount"]
            days = max((item["date"] - date_ref).days, 0)
            weighted += amount * days
            present += amount / ((1.0 + rate) ** (days / 30.0))
        return (weighted / total if total else 0.0), present

    def _rfq_effective_unit_cost(self, basis):
        """Custo unitário usado na pontuação, conforme a base da rodada."""
        self.ensure_one()
        if not self.product_qty:
            return 0.0
        rate = self.order_id.currency_rate or 1.0
        if basis == "subtotal":
            amount = self.price_subtotal
        elif basis == "total":
            amount = self.price_total
        else:
            amount = self.rfq_present_value
        return amount / rate / self.product_qty
