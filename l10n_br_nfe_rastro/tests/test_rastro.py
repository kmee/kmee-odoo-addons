# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRastro(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context, tracking_disable=True, test_queue_job_no_delay=True
            )
        )
        cls.wizard_model = cls.env["stock.invoice.onshipping"]
        cls.company = cls.env.ref("base.main_company")
        cls.env.user.company_ids += cls.company
        cls.env.user.company_id = cls.company
        cls.product = cls.env["product.product"].create(
            {"name": "Tracked product", "detailed_type": "product", "tracking": "lot"}
        )

    def _lot(self, name="LOT-001", **vals):
        return self.env["stock.lot"].create(
            dict(
                {
                    "name": name,
                    "product_id": self.product.id,
                    "company_id": self.env.company.id,
                },
                **vals,
            )
        )

    # ------------------------------------------------------------------
    # _get_move_line_rastro_vals
    # ------------------------------------------------------------------
    def test_move_line_without_lot_has_no_rastro(self):
        """
        Given a move line without lot
        When the rastro values are built
        Then nothing is returned (False)
        """
        move_line = self.env["stock.move.line"].new({"product_id": self.product.id})
        self.assertFalse(self.wizard_model._get_move_line_rastro_vals(move_line))

    def test_move_line_vals_with_lot_and_expiration(self):
        """
        Given a move line with a lot expiring on 2030-05-20 and qty done 7
        When the rastro values are built
        Then number, quantity and validity date (date only) are filled
        """
        lot = self._lot(expiration_date=datetime(2030, 5, 20, 10, 0))
        move_line = self.env["stock.move.line"].new(
            {"product_id": self.product.id, "lot_id": lot.id, "qty_done": 7.0}
        )
        vals = self.wizard_model._get_move_line_rastro_vals(move_line)
        self.assertEqual(vals["nfe40_nLote"], "LOT-001")
        self.assertEqual(vals["nfe40_qLote"], 7.0)
        self.assertEqual(vals["nfe40_dVal"].isoformat(), "2030-05-20")
        self.assertNotIn("nfe40_dFab", vals)

    def test_move_line_vals_with_production_date(self):
        """
        Given a lot with production date and no expiration
        When the rastro values are built
        Then the manufacturing date is filled as a date and no validity is set
        """
        lot = self._lot(production_date=datetime(2029, 1, 15, 8, 0))
        move_line = self.env["stock.move.line"].new(
            {"product_id": self.product.id, "lot_id": lot.id, "qty_done": 1.0}
        )
        vals = self.wizard_model._get_move_line_rastro_vals(move_line)
        self.assertEqual(vals["nfe40_dFab"].isoformat(), "2029-01-15")
        self.assertNotIn("nfe40_dVal", vals)

    # ------------------------------------------------------------------
    # invoice generation from a picking (integration)
    # ------------------------------------------------------------------
    def _deliver_picking(self):
        """Deliver demo picking 1 with a tracked lot on the first move only."""
        picking = self.env.ref("l10n_br_stock_account.main_company-picking_1")
        extra = self.env.ref("l10n_br_stock_account.main_company-move_1_3")
        extra.unlink()
        tracked_move = self.env.ref("l10n_br_stock_account.main_company-move_1_1")
        plain_move = self.env.ref("l10n_br_stock_account.main_company-move_1_2")
        self.assertNotEqual(tracked_move.product_id, plain_move.product_id)
        tracked_move.product_id.tracking = "lot"
        lot = self.env["stock.lot"].create(
            {
                "name": "LOT-NFE",
                "product_id": tracked_move.product_id.id,
                "company_id": self.company.id,
                "expiration_date": datetime(2031, 3, 31, 12, 0),
                "production_date": datetime(2030, 3, 1, 12, 0),
            }
        )
        picking.action_confirm()
        picking.action_assign()
        tracked_move.write(
            {
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": tracked_move.product_id.id,
                            "product_uom_id": tracked_move.product_uom.id,
                            "location_id": tracked_move.location_id.id,
                            "location_dest_id": tracked_move.location_dest_id.id,
                            "picking_id": picking.id,
                            "lot_id": lot.id,
                            "qty_done": tracked_move.product_uom_qty,
                        },
                    )
                ]
            }
        )
        plain_move.quantity_done = plain_move.product_uom_qty
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        return picking, tracked_move, plain_move

    def _invoice_picking(self, picking):
        wizard_obj = self.wizard_model.with_context(
            active_ids=picking.ids, active_model=picking._name
        )
        values = wizard_obj.default_get(list(wizard_obj.fields_get().keys()))
        values.update({"group": "partner_product"})
        wizard = wizard_obj.create(values)
        wizard.onchange_group()
        wizard.action_generate()
        return self.env["account.move"].search([("picking_ids", "in", picking.ids)])

    def test_invoice_from_picking_fills_rastro_of_tracked_line(self):
        """
        Given a delivered picking with a lot-tracked product and a plain one
        When the invoice is generated from the picking wizard
        Then the fiscal line of the tracked product carries the NF-e rastro
        (lot, quantity, manufacturing and validity dates) and the plain
        product line has none
        """
        picking, tracked_move, plain_move = self._deliver_picking()
        invoice = self._invoice_picking(picking)
        self.assertTrue(invoice)
        tracked_line = invoice.invoice_line_ids.filtered(
            lambda line: line.product_id == tracked_move.product_id
        )
        plain_line = invoice.invoice_line_ids.filtered(
            lambda line: line.product_id == plain_move.product_id
        )
        self.assertEqual(len(tracked_line), 1)
        rastro = tracked_line.nfe40_rastro
        self.assertEqual(len(rastro), 1)
        self.assertEqual(rastro.nfe40_nLote, "LOT-NFE")
        self.assertEqual(rastro.nfe40_qLote, tracked_move.product_uom_qty)
        self.assertEqual(rastro.nfe40_dVal.isoformat(), "2031-03-31")
        self.assertEqual(rastro.nfe40_dFab.isoformat(), "2030-03-01")
        self.assertFalse(plain_line.nfe40_rastro)
