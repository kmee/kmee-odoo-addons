# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.base.tests.common import BaseCommon


class DdmrpPurchaseRequestCommon(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.buy_route = cls.env.ref("purchase_stock.route_warehouse0_buy")
        cls.vendor_a = cls.env["res.partner"].create({"name": "Vendor A"})
        cls.vendor_b = cls.env["res.partner"].create({"name": "Vendor B"})
        cls.profile = cls.env.ref(
            "ddmrp.stock_buffer_profile_replenish_purchased_short_low"
        )
        cls.adu_fixed = cls.env.ref("ddmrp.adu_calculation_method_fixed")

    @classmethod
    def _create_product(cls, name, purchase_request=True):
        product = cls.env["product.product"].create(
            {
                "name": name,
                "is_storable": True,
                "route_ids": [(6, 0, cls.buy_route.ids)],
                "seller_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": cls.vendor_a.id,
                            "price": 10.0,
                            "delay": 10,
                            "sequence": 1,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "partner_id": cls.vendor_b.id,
                            "price": 9.0,
                            "delay": 30,
                            "sequence": 2,
                        },
                    ),
                ],
            }
        )
        product.product_tmpl_id.purchase_request = purchase_request
        return product

    @classmethod
    def _create_buffer(cls, product):
        buffer = cls.env["stock.buffer"].create(
            {
                "product_id": product.id,
                "warehouse_id": cls.warehouse.id,
                "location_id": cls.warehouse.lot_stock_id.id,
                "buffer_profile_id": cls.profile.id,
                "adu_calculation_method": cls.adu_fixed.id,
                "adu_fixed": 10.0,
            }
        )
        buffer.cron_actions()
        return buffer

    def _procure(self, buffer, partner=None):
        wizard = (
            self.env["make.procurement.buffer"]
            .with_context(
                active_model="stock.buffer",
                active_ids=buffer.ids,
                active_id=buffer.id,
            )
            .create({"partner_id": partner.id if partner else False})
        )
        wizard.make_procurement()
        buffer.invalidate_recordset()
        buffer.cron_actions()
