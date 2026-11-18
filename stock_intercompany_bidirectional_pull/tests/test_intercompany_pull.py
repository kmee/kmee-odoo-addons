# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIntercompanyPull(TransactionCase):
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
        Company = cls.env["res.company"]
        cls.company_a = Company.create({"name": "Pull Company A"})
        cls.company_b = Company.create({"name": "Pull Company B"})
        cls.wh_a = cls._warehouse(cls.company_a)
        cls.wh_b = cls._warehouse(cls.company_b)
        cls.company_a.write(
            {
                "intercompany_out_type_id": cls.wh_a.out_type_id.id,
                "intercompany_in_type_id": cls.wh_a.in_type_id.id,
            }
        )
        cls.company_b.write(
            {
                "intercompany_out_type_id": cls.wh_b.out_type_id.id,
                "intercompany_in_type_id": cls.wh_b.in_type_id.id,
            }
        )
        cls.env.user.write(
            {
                "company_id": cls.company_a.id,
                "company_ids": [(4, cls.company_a.id), (4, cls.company_b.id)],
            }
        )
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                allowed_company_ids=[cls.company_a.id, cls.company_b.id],
            )
        )
        cls.customers = cls.env.ref("stock.stock_location_customers")
        cls.suppliers = cls.env.ref("stock.stock_location_suppliers")
        cls.product = cls.env["product.product"].create(
            {"name": "Pull Product", "type": "product", "company_id": False}
        )
        cls.uom = cls.env.ref("uom.product_uom_unit")

    @classmethod
    def _warehouse(cls, company):
        return cls.env["stock.warehouse"].search(
            [("company_id", "=", company.id)], limit=1
        )

    def _picking(self, picking_type, partner, qty=5.0):
        loc_src = picking_type.default_location_src_id
        loc_dst = picking_type.default_location_dest_id
        if picking_type.code == "incoming":
            loc_src = self.suppliers
        elif picking_type.code == "outgoing":
            loc_dst = self.customers
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "partner_id": partner.id,
                "location_id": loc_src.id,
                "location_dest_id": loc_dst.id,
                "company_id": self.company_a.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "product_uom": self.uom.id,
                            "location_id": loc_src.id,
                            "location_dest_id": loc_dst.id,
                        },
                    )
                ],
            }
        )
        return picking

    def test_receipt_confirm_creates_outgoing_counterpart(self):
        """Given a receipt in company A from company B (a company partner),
        When it is confirmed,
        Then B gets a draft delivery for the same qty, linked to the receipt."""
        receipt = self._picking(self.wh_a.in_type_id, self.company_b.partner_id, 7.0)
        receipt.action_confirm()
        counter = receipt.counterpart_picking_id
        self.assertTrue(counter)
        self.assertEqual(counter.company_id, self.company_b)
        self.assertEqual(counter.picking_type_id, self.wh_b.out_type_id)
        self.assertEqual(counter.origin, receipt.name)
        self.assertEqual(counter.location_id, self.wh_b.lot_stock_id)
        self.assertEqual(counter.location_dest_id, self.customers)
        self.assertEqual(counter.partner_id, self.company_a.partner_id)
        self.assertEqual(counter.state, "draft")
        self.assertEqual(counter.move_ids.product_id, self.product)
        self.assertEqual(counter.move_ids.product_uom_qty, 7.0)

    def test_delivery_confirm_creates_incoming_counterpart(self):
        """Given a delivery in company A to company B,
        When it is confirmed,
        Then B gets a draft receipt from customers into its stock."""
        delivery = self._picking(self.wh_a.out_type_id, self.company_b.partner_id, 3.0)
        delivery.action_confirm()
        counter = delivery.counterpart_picking_id
        self.assertTrue(counter)
        self.assertEqual(counter.company_id, self.company_b)
        self.assertEqual(counter.picking_type_id, self.wh_b.in_type_id)
        self.assertEqual(counter.location_id, self.customers)
        self.assertEqual(counter.location_dest_id, self.wh_b.lot_stock_id)
        self.assertEqual(counter.move_ids.product_uom_qty, 3.0)
        self.assertEqual(counter.origin, delivery.name)

    def test_no_counterpart_for_regular_partner(self):
        """Given a receipt from an ordinary company partner (not a res.company),
        When confirmed,
        Then no counterpart is created."""
        vendor = self.env["res.partner"].create(
            {"name": "Vendor Inc", "is_company": True}
        )
        receipt = self._picking(self.wh_a.in_type_id, vendor)
        receipt.action_confirm()
        self.assertFalse(receipt.counterpart_picking_id)

    def test_no_counterpart_for_individual_partner(self):
        """Given a partner that is not a company,
        When the picking is confirmed,
        Then nothing is mirrored even if the name matches."""
        person = self.env["res.partner"].create({"name": "Joe", "is_company": False})
        receipt = self._picking(self.wh_a.in_type_id, person)
        before = self.env["stock.picking"].sudo().search_count([])
        receipt.action_confirm()
        self.assertFalse(receipt.counterpart_picking_id)
        self.assertEqual(self.env["stock.picking"].sudo().search_count([]), before)

    def test_internal_picking_has_no_counterpart(self):
        """Given an internal transfer addressed to a company partner,
        When confirmed,
        Then no counterpart (only receipts and deliveries are mirrored)."""
        picking = self._picking(self.wh_a.int_type_id, self.company_b.partner_id)
        picking.action_confirm()
        self.assertFalse(picking.counterpart_picking_id)

    def test_cancel_cancels_counterpart(self):
        """Given a confirmed receipt with its counterpart,
        When the receipt is canceled,
        Then the counterpart is canceled as well."""
        receipt = self._picking(self.wh_a.in_type_id, self.company_b.partner_id)
        receipt.action_confirm()
        counter = receipt.counterpart_picking_id
        self.assertNotEqual(counter.state, "cancel")
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancel")
        self.assertEqual(counter.sudo().state, "cancel")

    def test_cancel_without_counterpart(self):
        """Given a picking without counterpart,
        When canceled,
        Then it just cancels."""
        vendor = self.env["res.partner"].create({"name": "Vendor"})
        receipt = self._picking(self.wh_a.in_type_id, vendor)
        receipt.action_confirm()
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancel")

    def test_counterpart_link_is_not_copied(self):
        """Given a picking linked to a counterpart,
        When it is duplicated,
        Then the copy does not keep the link."""
        receipt = self._picking(self.wh_a.in_type_id, self.company_b.partner_id)
        receipt.action_confirm()
        self.assertTrue(receipt.counterpart_picking_id)
        self.assertFalse(receipt.copy().counterpart_picking_id)

    def test_confirm_with_stock_user_without_access_to_other_company(self):
        """Given a stock user that only belongs to company A,
        When confirming a receipt from company B,
        Then the counterpart in B is still created (sudo) and the user cannot read it."""
        user = self.env["res.users"].create(
            {
                "name": "Stock A",
                "login": "stock_a_pull",
                "company_id": self.company_a.id,
                "company_ids": [(6, 0, self.company_a.ids)],
                "groups_id": [
                    (6, 0, [self.env.ref("stock.group_stock_user").id]),
                ],
            }
        )
        receipt = self._picking(self.wh_a.in_type_id, self.company_b.partner_id)
        receipt.with_user(user).with_context(
            allowed_company_ids=[self.company_a.id]
        ).action_confirm()
        counter = receipt.counterpart_picking_id
        self.assertTrue(counter)
        self.assertEqual(counter.company_id, self.company_b)
        self.assertEqual(
            self.env["stock.picking"]
            .with_user(user)
            .with_context(allowed_company_ids=[self.company_a.id])
            .search_count([("id", "=", counter.id)]),
            0,
        )

    def test_vals_for_incoming_use_in_type_warehouse(self):
        """Given company B with different warehouses for its IN and OUT types,
        When the incoming counterpart values are built,
        Then the destination is the stock of the IN type warehouse."""
        wh_extra = self.env["stock.warehouse"].create(
            {
                "name": "Extra B",
                "code": "XB",
                "company_id": self.company_b.id,
            }
        )
        self.company_b.intercompany_in_type_id = wh_extra.in_type_id
        delivery = self._picking(self.wh_a.out_type_id, self.company_b.partner_id)
        vals = delivery._get_counterpart_picking_vals(self.company_b, incoming=True)
        self.assertEqual(vals["picking_type_id"], wh_extra.in_type_id.id)
        self.assertEqual(vals["location_dest_id"], wh_extra.lot_stock_id.id)
