# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class RfqRoundCommon(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, mail_notrack=True))
        Partner = cls.env["res.partner"]
        cls.vendor_1 = Partner.create(
            {"name": "Vendor One", "email": "one@example.com", "is_company": True}
        )
        cls.vendor_2 = Partner.create(
            {"name": "Vendor Two", "email": "two@example.com", "is_company": True}
        )
        cls.vendor_3 = Partner.create({"name": "Vendor Three", "is_company": True})
        Product = cls.env["product.product"]
        cls.product_a = Product.create(
            {
                "name": "Item A",
                "default_code": "ITEM-A",
                "is_storable": True,
                "seller_ids": [
                    (0, 0, {"partner_id": cls.vendor_1.id, "price": 10.0}),
                    (0, 0, {"partner_id": cls.vendor_2.id, "price": 11.0}),
                ],
            }
        )
        cls.product_b = Product.create(
            {
                "name": "Item B",
                "default_code": "ITEM-B",
                "is_storable": True,
                "seller_ids": [
                    (0, 0, {"partner_id": cls.vendor_2.id, "price": 20.0}),
                    (0, 0, {"partner_id": cls.vendor_3.id, "price": 19.0}),
                ],
            }
        )
        cls.request = cls.env["purchase.request"].create(
            {
                "line_ids": [
                    (0, 0, {"product_id": cls.product_a.id, "product_qty": 100.0}),
                    (0, 0, {"product_id": cls.product_b.id, "product_qty": 50.0}),
                ]
            }
        )
        cls.request.button_to_approve()
        cls.request.button_approved()

    def _make_round(self, vendors=None):
        wizard = (
            self.env["purchase.request.line.make.rfq.round"]
            .with_context(
                active_model="purchase.request.line",
                active_ids=self.request.line_ids.ids,
            )
            .create({"vendor_ids": [(6, 0, vendors.ids)] if vendors else []})
        )
        action = wizard.action_create()
        return self.env["purchase.rfq.round"].browse(action["res_id"])

    def _quote(self, rfq_round, vendor, product):
        return rfq_round.order_ids.filtered(
            lambda o: o.partner_id == vendor
        ).order_line.filtered(lambda line: line.product_id == product)
