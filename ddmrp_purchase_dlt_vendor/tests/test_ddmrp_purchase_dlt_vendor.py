# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestDdmrpPurchaseDltVendor(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        wh = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        Partner = cls.env["res.partner"]
        cls.fast = Partner.create({"name": "Fast"})
        cls.slow = Partner.create({"name": "Slow"})
        cls.slowest = Partner.create({"name": "Slowest"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "DLT item",
                "is_storable": True,
                "seller_ids": [
                    (0, 0, {"partner_id": cls.fast.id, "delay": 10, "sequence": 1}),
                    (
                        0,
                        0,
                        {
                            "partner_id": cls.slow.id,
                            "delay": 30,
                            "sequence": 2,
                            "rfq_approved": True,
                        },
                    ),
                    (0, 0, {"partner_id": cls.slowest.id, "delay": 45, "sequence": 3}),
                ],
            }
        )
        cls.profile = cls.env.ref(
            "ddmrp.stock_buffer_profile_replenish_purchased_short_low"
        ).copy()
        cls.buffer = cls.env["stock.buffer"].create(
            {
                "product_id": cls.product.id,
                "warehouse_id": wh.id,
                "location_id": wh.lot_stock_id.id,
                "buffer_profile_id": cls.profile.id,
                "adu_calculation_method": cls.env.ref(
                    "ddmrp.adu_calculation_method_fixed"
                ).id,
                "adu_fixed": 10.0,
            }
        )

    def test_01_first_vendor_default(self):
        self.assertEqual(self.profile.dlt_vendor_policy, "first")
        self.assertEqual(self.buffer.dlt, 10)

    def test_02_worst_approved(self):
        self.profile.dlt_vendor_policy = "worst_approved"
        self.assertEqual(self.buffer.dlt, 30)

    def test_03_worst_approved_without_approved_uses_all(self):
        self.product.seller_ids.rfq_approved = False
        self.profile.dlt_vendor_policy = "worst_approved"
        self.assertEqual(self.buffer.dlt, 45)

    def test_04_worst(self):
        self.profile.dlt_vendor_policy = "worst"
        self.assertEqual(self.buffer.dlt, 45)
