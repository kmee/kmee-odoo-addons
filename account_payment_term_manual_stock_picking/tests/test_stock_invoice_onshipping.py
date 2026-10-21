# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockInvoiceOnshipping(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.term = cls.env["account.payment.term"].create(
            {
                "name": "50% in 30 days, 50% in 60 days",
                "line_ids": [
                    (0, 0, {"value": "percent", "value_amount": 50.0, "nb_days": 30}),
                    (0, 0, {"value": "percent", "value_amount": 50.0, "nb_days": 60}),
                ],
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Partner"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Product",
                "detailed_type": "product",
                "list_price": 1000.0,
                "standard_price": 1000.0,
                "invoice_policy": "order",
                "purchase_method": "purchase",
            }
        )

    def _edit_manual_term(self, order):
        manual = order.manual_payment_term_id
        manual.line_ids.filtered(lambda x: x.nb_days == 30).write(
            {"value_amount": 30.0, "fixed_date": date(2024, 2, 20)}
        )
        manual.line_ids.filtered(lambda x: x.nb_days == 60).write(
            {"value_amount": 70.0, "fixed_date": date(2024, 4, 10)}
        )

    def _sale_order(self):
        vals = {}
        if "fiscal_operation_id" in self.env["sale.order"]._fields:
            # com o l10n_br_sale instalado (suite completa) o faturamento segue o
            # caminho fiscal; estes testes cobrem o fluxo padrao do Odoo
            vals["fiscal_operation_id"] = False
        if "order_sequence" in self.env["sale.order"]._fields:
            # com a cotacao isolada instalada, so o pedido com sequencia propria confirma
            vals["order_sequence"] = True
        order = self.env["sale.order"].create(
            {
                **vals,
                "partner_id": self.partner.id,
                "payment_term_id": self.term.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "price_unit": 1000.0,
                            "tax_id": False,
                        },
                    )
                ],
            }
        )
        order._update_manual_payment_term_id(self.term)
        return order

    def _purchase_order(self):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "payment_term_id": self.term.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                            "price_unit": 1000.0,
                            "taxes_id": False,
                        },
                    )
                ],
            }
        )
        order._update_manual_payment_term_id(self.term)
        return order

    def _deliver_and_invoice(self, picking):
        picking.write({"invoice_state": "2binvoiced"})
        picking.move_ids.write({"invoice_state": "2binvoiced"})
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.button_validate()
        wizard_model = self.env["stock.invoice.onshipping"].with_context(
            active_ids=picking.ids, active_model="stock.picking"
        )
        values = wizard_model.default_get(wizard_model.fields_get().keys())
        wizard = wizard_model.create(values)
        wizard.action_generate()
        invoice = self.env["account.move"].search([("picking_ids", "in", picking.ids)])
        self.assertEqual(len(invoice), 1)
        return invoice

    def _installments(self, invoice):
        lines = invoice.line_ids.filtered(lambda x: x.display_type == "payment_term")
        return sorted((x.date_maturity, abs(x.balance)) for x in lines)

    def _expected_installments(self, invoice):
        """30% on the fixed date and the balance on the other one."""
        first = round(invoice.amount_total * 0.3, 2)
        return [
            (date(2024, 2, 20), first),
            (date(2024, 4, 10), round(invoice.amount_total - first, 2)),
        ]

    def test_sale_picking_invoice_copies_manual_term(self):
        order = self._sale_order()
        self._edit_manual_term(order)
        order.action_confirm()
        invoice = self._deliver_and_invoice(order.picking_ids)
        self.assertEqual(invoice.move_type, "out_invoice")
        self.assertEqual(invoice.invoice_payment_term_id, self.term)
        self.assertTrue(invoice.manual_payment_term_id)
        self.assertNotEqual(
            invoice.manual_payment_term_id, order.manual_payment_term_id
        )
        self.assertEqual(
            self._installments(invoice),
            self._expected_installments(invoice),
        )

    def test_purchase_picking_invoice_copies_manual_term(self):
        order = self._purchase_order()
        self._edit_manual_term(order)
        order.button_confirm()
        invoice = self._deliver_and_invoice(order.picking_ids)
        self.assertEqual(invoice.move_type, "in_invoice")
        self.assertEqual(invoice.invoice_payment_term_id, self.term)
        self.assertTrue(invoice.manual_payment_term_id)
        self.assertEqual(
            self._installments(invoice),
            self._expected_installments(invoice),
        )

    def test_picking_without_order_keeps_standard_behavior(self):
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.partner.id,
                "picking_type_id": self.env.ref("stock.picking_type_out").id,
                "location_id": self.env.ref("stock.stock_location_stock").id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Product",
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "product_uom": self.product.uom_id.id,
                            "location_id": self.env.ref(
                                "stock.stock_location_stock"
                            ).id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        invoice = self._deliver_and_invoice(picking)
        self.assertFalse(invoice.manual_payment_term_id)
