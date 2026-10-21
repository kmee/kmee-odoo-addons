# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPeriodBlanketOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                test_queue_job_no_delay=True,
                no_reset_password=True,
            )
        )
        categ_unit = cls.env.ref("uom.product_uom_categ_unit")
        cls.uom_period = cls.env["uom.uom"].create(
            {
                "name": "License-Month",
                "category_id": categ_unit.id,
                "uom_type": "bigger",
                "factor_inv": 2,
                "use_period_quantity": True,
            }
        )
        cls.uom_plain = cls.env["uom.uom"].create(
            {
                "name": "Plain-Box",
                "category_id": categ_unit.id,
                "uom_type": "bigger",
                "factor_inv": 3,
            }
        )
        cls.template = cls.env["contract.template"].create({"name": "Template"})
        cls.product_period = cls.env["product.product"].create(
            {
                "name": "Period service",
                "type": "service",
                "uom_id": cls.uom_period.id,
                "uom_po_id": cls.uom_period.id,
                "is_contract": True,
                "property_contract_template_id": cls.template.id,
            }
        )
        cls.product_plain = cls.env["product.product"].create(
            {
                "name": "Plain service",
                "type": "service",
                "uom_id": cls.uom_plain.id,
                "uom_po_id": cls.uom_plain.id,
                "is_contract": True,
                "property_contract_template_id": cls.template.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "BO Customer"})
        cls.pricelist = cls.env["product.pricelist"].create(
            {"name": "BO Pricelist", "currency_id": cls.env.company.currency_id.id}
        )
        cls.blanket = cls.env["sale.blanket.order"].create(
            {
                "partner_id": cls.partner.id,
                "pricelist_id": cls.pricelist.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product_period.id,
                            "product_uom": cls.uom_period.id,
                            "original_uom_qty": 24.0,
                            "price_unit": 10.0,
                            "period_qty": 2.0,
                            "period_count": 12,
                            "recurring_rule_type": "monthly",
                            "date_start": "2026-01-01",
                            "date_end": "2026-12-31",
                        },
                    )
                ],
            }
        )
        cls.bo_line = cls.blanket.line_ids

    def _order_vals(self, **extra):
        vals = {"partner_id": self.partner.id}
        if "fiscal_operation_id" in self.env["sale.order"]._fields:
            vals["fiscal_operation_id"] = False
        vals.update(extra)
        return vals

    def _so_line(self, product, **extra):
        order = self.env["sale.order"].create(self._order_vals())
        vals = {
            "order_id": order.id,
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "price_unit": 10.0,
            "date_start": "2026-01-01",
        }
        vals.update(extra)
        return self.env["sale.order.line"].create(vals)

    def test_uom_flag_default_false(self):
        """Given a regular unit of measure,
        When no flag is set,
        Then period based calculation is off."""
        self.assertFalse(self.env.ref("uom.product_uom_unit").use_period_quantity)
        self.assertTrue(self.uom_period.use_period_quantity)

    def test_line_flag_related_to_product_uom(self):
        """Given products with and without the period UoM,
        When order lines are created,
        Then use_period_quantity follows the product UoM."""
        self.assertTrue(self._so_line(self.product_period).use_period_quantity)
        self.assertFalse(self._so_line(self.product_plain).use_period_quantity)

    def test_write_period_recomputes_quantity(self):
        """Given a line with the period UoM,
        When period_qty and period_count are written,
        Then product_uom_qty becomes their product."""
        line = self._so_line(self.product_period)
        line.write({"period_qty": 3.0, "period_count": 4})
        self.assertEqual(line.product_uom_qty, 12.0)

    def test_write_only_period_count_uses_current_period_qty(self):
        """Given a line with period_qty 5,
        When only period_count changes to 2,
        Then the quantity is 10."""
        line = self._so_line(self.product_period, period_qty=5.0, period_count=1)
        line.write({"period_count": 2})
        self.assertEqual(line.product_uom_qty, 10.0)

    def test_write_period_ignored_without_period_uom(self):
        """Given a line whose UoM is not period based,
        When period fields are written along with a quantity,
        Then the written quantity is kept untouched."""
        line = self._so_line(self.product_plain)
        line.write({"period_qty": 3.0, "period_count": 4, "product_uom_qty": 7.0})
        self.assertEqual(line.product_uom_qty, 7.0)

    def test_write_applies_per_record(self):
        """Given two lines with different periods,
        When both are written in one call with new period_count,
        Then each quantity uses its own period_qty."""
        line1 = self._so_line(self.product_period, period_qty=2.0)
        line2 = self._so_line(self.product_period, period_qty=5.0)
        (line1 | line2).write({"period_count": 3})
        self.assertEqual(line1.product_uom_qty, 6.0)
        self.assertEqual(line2.product_uom_qty, 15.0)

    def test_onchange_period_sets_quantity_and_end_date(self):
        """Given a period UoM line with 4 monthly periods from 2026-01-01,
        When the period onchange runs,
        Then quantity = qty*count and date_end is 2026-04-30."""
        line = self._so_line(self.product_period)
        line.recurring_rule_type = "monthly"
        line.period_qty = 2.0
        line.period_count = 4
        line._onchange_period()
        self.assertEqual(line.product_uom_qty, 8.0)
        self.assertEqual(line.date_end, date(2026, 4, 30))

    def test_onchange_period_without_start_clears_end(self):
        """Given a period UoM line with no start date,
        When the onchange runs,
        Then date_end is cleared."""
        line = self._so_line(self.product_period, date_start=False)
        line.date_end = date(2026, 1, 1)
        line._onchange_period()
        self.assertFalse(line.date_end)

    def test_onchange_period_plain_uom_keeps_base_behavior(self):
        """Given a plain UoM contract line,
        When the period onchange runs,
        Then quantity is untouched and the end date still follows the base
        product_contract_period rule (the override must call super)."""
        line = self._so_line(
            self.product_plain, product_uom_qty=9.0, date_end="2030-01-01"
        )
        line.period_qty = 4.0
        line.recurring_rule_type = "monthly"
        line.period_count = 2
        line._onchange_period()
        self.assertEqual(line.product_uom_qty, 9.0)
        self.assertEqual(line.date_end, date(2026, 2, 28))

    def test_protected_fields_unprotected_for_new_bo_qty(self):
        """Given the context of a line created from a B.O. with zero original qty,
        When protected fields are requested,
        Then quantity and original_bo_qty are not protected; otherwise they are."""
        line = self._so_line(self.product_period)
        base = line._get_protected_fields()
        self.assertIn("product_uom_qty", base)
        ctx = {"product_uom_qty": 3.0, "original_bo_qty": 0}
        free = line.with_context(check_qty_unprotect=ctx)._get_protected_fields()
        self.assertNotIn("product_uom_qty", free)
        self.assertNotIn("original_bo_qty", free)
        ctx_nonzero = {"product_uom_qty": 3.0, "original_bo_qty": 5}
        kept = line.with_context(
            check_qty_unprotect=ctx_nonzero
        )._get_protected_fields()
        self.assertIn("product_uom_qty", kept)

    def test_so_line_to_blanket_line_values_carry_periods(self):
        """Given a quotation line with periods and dates,
        When the blanket order line values are prepared,
        Then period qty, count and dates are carried."""
        line = self._so_line(
            self.product_period,
            period_qty=2.0,
            period_count=6,
            date_end="2026-06-30",
        )
        vals = line._prepare_sale_order_line_values()
        self.assertEqual(vals["period_qty"], 2.0)
        self.assertEqual(vals["period_count"], 6)
        self.assertEqual(vals["date_start"], date(2026, 1, 1))
        self.assertEqual(vals["date_end"], date(2026, 6, 30))
        self.assertEqual(vals["product_id"], self.product_period.id)

    def test_blanket_order_line_values_for_quotation_carry_periods(self):
        """Given a blanket order line with periods,
        When the quotation line values are prepared from it,
        Then period qty, count and dates come from the B.O. line."""
        order = self.env["sale.order"].create(self._order_vals())
        vals = order._prepare_blanket_order_line_values(self.bo_line)
        self.assertEqual(vals["period_qty"], 2.0)
        self.assertEqual(vals["period_count"], 12)
        self.assertEqual(vals["date_start"], date(2026, 1, 1))
        self.assertEqual(vals["date_end"], date(2026, 12, 31))
        self.assertEqual(vals["blanket_order_line_id"], self.bo_line.id)

    def test_reference_quotation_copies_periods_from_blanket(self):
        """Given a blanket order with a period line,
        When a reference quotation is created from it,
        Then the quotation line carries qty/count/dates of the B.O. line."""
        action = self.blanket.action_create_reference_quotation()
        quotation = self.env["sale.order"].browse(action["res_id"])
        line = quotation.order_line
        self.assertEqual(len(line), 1)
        self.assertEqual(line.period_qty, 2.0)
        self.assertEqual(line.period_count, 12)
        self.assertEqual(line.date_start, date(2026, 1, 1))
        self.assertEqual(line.blanket_order_line_id, self.bo_line)

    def test_new_blanket_line_from_quotation_line(self):
        """Given a quotation line with periods not yet on the blanket order,
        When the blanket order line is created from it,
        Then the new B.O. line keeps the period data."""
        quotation = self.env["sale.order"].create(
            self._order_vals(
                blanket_order_id=self.blanket.id, blanket_order_type="amendment"
            )
        )
        line = self.env["sale.order.line"].create(
            {
                "order_id": quotation.id,
                "product_id": self.product_plain.id,
                "product_uom": self.uom_plain.id,
                "product_uom_qty": 4.0,
                "price_unit": 5.0,
                "period_qty": 4.0,
                "period_count": 3,
                "date_start": "2026-02-01",
            }
        )
        line.create_blanket_order_line()
        new_line = self.blanket.line_ids.filtered(
            lambda bol: bol.product_id == self.product_plain
        )
        self.assertEqual(len(new_line), 1)
        self.assertEqual(new_line.period_qty, 4.0)
        self.assertEqual(new_line.period_count, 3)
        self.assertEqual(new_line.date_start, date(2026, 2, 1))

    def _wizard(self):
        return (
            self.env["sale.blanket.order.wizard"]
            .with_context(
                active_model="sale.blanket.order",
                active_id=self.blanket.id,
                active_ids=self.blanket.ids,
            )
            .create({})
        )

    def test_wizard_default_lines_carry_periods(self):
        """Given an open blanket order with a period line,
        When the order wizard opens,
        Then its lines carry the B.O. line period data."""
        self.blanket.sudo().write({"state": "open"})
        wizard = self._wizard()
        self.assertEqual(len(wizard.line_ids), 1)
        wline = wizard.line_ids
        self.assertEqual(wline.period_qty, 2.0)
        self.assertEqual(wline.period_count, 12.0)
        self.assertEqual(wline.date_start, date(2026, 1, 1))
        self.assertEqual(wline.date_end, date(2026, 12, 31))

    def test_wizard_so_line_values_use_reference_quotation(self):
        """Given a reference quotation line with edited periods,
        When the wizard prepares the sale order line,
        Then the periods come from the quotation line (context so_reference_id)."""
        self.blanket.sudo().write({"state": "open"})
        action = self.blanket.action_create_reference_quotation()
        quotation = self.env["sale.order"].browse(action["res_id"])
        quotation.order_line.write({"period_qty": 3.0, "period_count": 5})
        wizard = self._wizard()
        wline = wizard.line_ids
        plain = wizard._prepare_so_line_vals(wline)
        self.assertNotIn("period_count", plain)
        vals = wizard.with_context(so_reference_id=quotation.id)._prepare_so_line_vals(
            wline
        )
        self.assertEqual(vals["period_qty"], 3.0)
        self.assertEqual(vals["period_count"], 5)
        self.assertEqual(vals["date_start"], date(2026, 1, 1))

    def test_create_sale_order_from_wizard_recomputes_quantities(self):
        """Given a reference quotation of 6 periods of 2 licenses,
        When the sale order is created from the B.O. via the wizard,
        Then the new order line has quantity 12 recomputed from the periods."""
        self.blanket.sudo().write({"state": "open"})
        action = self.blanket.action_create_reference_quotation()
        quotation = self.env["sale.order"].browse(action["res_id"])
        quotation.order_line.write(
            {"period_qty": 2.0, "period_count": 6, "product_uom_qty": 12.0}
        )
        result = self.blanket.with_context(
            so_reference_id=quotation.id
        ).create_sale_order_from_wizard(quotation.order_line)
        order = self.env["sale.order"].browse(result["domain"][0][2])
        self.assertEqual(len(order), 1)
        line = order.order_line
        self.assertEqual(line.period_qty, 2.0)
        self.assertEqual(line.period_count, 6)
        self.assertEqual(line.product_uom_qty, 12.0)
        self.assertEqual(line.date_end, date(2026, 6, 30))
