# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools import float_is_zero

COMMITTED_STATES = ("purchase", "done")


class MisPurchaseCommitmentDue(models.Model):
    """Parcelas a pagar dos pedidos de compra confirmados e não faturados.

    Fonte "parecida com lançamento" para o MIS Builder (date, account_id,
    debit, credit, company_id): o saldo ainda não faturado de cada pedido,
    com impostos, distribuído pela condição de pagamento a partir da data
    prevista de recebimento, contra a conta a pagar do fornecedor. O valor a
    pagar fica no crédito, como no razão.
    """

    _name = "mis.purchase.commitment.due"
    _description = "Purchase Commitment by Due Date"
    _order = "date, id"

    name = fields.Char(required=True)
    date = fields.Date(string="Due Date", required=True, index=True)
    company_id = fields.Many2one("res.company", required=True, index=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    account_id = fields.Many2one("account.account", index=True)
    partner_id = fields.Many2one("res.partner", string="Vendor", index=True)
    purchase_order_id = fields.Many2one(
        "purchase.order", required=True, ondelete="cascade", index=True
    )
    payment_term_id = fields.Many2one("account.payment.term")
    debit = fields.Monetary(default=0.0)
    credit = fields.Monetary(default=0.0)
    amount = fields.Monetary(
        compute="_compute_amount", store=True, string="Amount to Pay"
    )

    @api.depends("debit", "credit")
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.credit - rec.debit

    @api.model
    def _sync_orders(self, orders):
        """Recria as parcelas dos pedidos informados."""
        orders = orders.exists()
        if not orders:
            return
        self.sudo().search([("purchase_order_id", "in", orders.ids)]).unlink()
        vals_list = []
        for order in orders.filtered(lambda o: o.state in COMMITTED_STATES):
            vals_list += self._prepare_order_installments(order)
        self.sudo().create(vals_list)

    @api.model
    def _get_posted_invoiced_qty(self, line):
        """Quantidade faturada em faturas lançadas (estornos abatem).

        O ``qty_invoiced`` do core conta também faturas em rascunho, que
        ainda não estão no razão nem no fluxo de caixa do MIS.
        """
        qty = 0.0
        for inv_line in line.invoice_lines:
            move = inv_line.move_id
            if move.state != "posted":
                continue
            inv_qty = inv_line.product_uom_id._compute_quantity(
                inv_line.quantity, line.product_uom
            )
            qty += -inv_qty if move.move_type == "in_refund" else inv_qty
        return qty

    @api.model
    def _get_uninvoiced_amount(self, order):
        """Saldo não faturado do pedido, com impostos, na moeda da empresa."""
        total = 0.0
        for line in order.order_line.filtered(lambda pol: not pol.display_type):
            if not line.product_qty:
                continue
            invoiced = self._get_posted_invoiced_qty(line)
            ratio = max(line.product_qty - invoiced, 0.0) / line.product_qty
            total += line.price_total * ratio
        return order.currency_id._convert(
            total,
            order.company_id.currency_id,
            order.company_id,
            order.date_order or fields.Date.today(),
        )

    @api.model
    def _get_reference_date(self, order):
        return (order.date_planned or order.date_approve or order.date_order).date()

    @api.model
    def _prepare_order_installments(self, order):
        company = order.company_id
        amount = self._get_uninvoiced_amount(order)
        if float_is_zero(amount, precision_rounding=company.currency_id.rounding):
            return []
        date_ref = self._get_reference_date(order)
        partner = order.partner_id.commercial_partner_id
        account = partner.with_company(company).property_account_payable_id
        base = {
            "company_id": company.id,
            "account_id": account.id,
            "partner_id": partner.id,
            "purchase_order_id": order.id,
            "payment_term_id": order.payment_term_id.id,
        }
        if order.payment_term_id:
            terms = order.payment_term_id._compute_terms(
                date_ref=date_ref,
                currency=company.currency_id,
                company=company,
                tax_amount=0.0,
                tax_amount_currency=0.0,
                sign=1,
                untaxed_amount=amount,
                untaxed_amount_currency=amount,
            )["line_ids"]
            installments = [(t["date"], t["company_amount"]) for t in terms]
        else:
            installments = [(date_ref, amount)]
        count = len(installments)
        return [
            dict(
                base,
                name=f"{order.name} ({index}/{count})" if count > 1 else order.name,
                date=due_date,
                credit=value if value > 0 else 0.0,
                debit=-value if value < 0 else 0.0,
            )
            for index, (due_date, value) in enumerate(installments, 1)
        ]

    @api.model
    def _cron_sync_all(self):
        orders = self.env["purchase.order"].search(
            [("state", "in", COMMITTED_STATES), ("invoice_status", "!=", "invoiced")]
        )
        stale = self.search([]).purchase_order_id - orders
        self._sync_orders(orders | stale)

    def action_sync_all(self):
        self._cron_sync_all()
        return True
