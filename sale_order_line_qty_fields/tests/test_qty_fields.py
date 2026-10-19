# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from lxml import etree

from odoo.tests.common import TransactionCase, tagged

QTY_GROUPS = {
    "qty_available_today": "sale_order_line_qty_fields.group_qty_available_today",
    "free_qty_today": "sale_order_line_qty_fields.group_free_qty_today",
    "free_qty": "sale_order_line_qty_fields.group_free_qty",
}


@tagged("post_install", "-at_install")
class TestSaleOrderLineQtyFields(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, no_reset_password=True)
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Stored Product", "type": "product", "list_price": 10.0}
        )
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.partner = cls.env["res.partner"].create({"name": "Qty Customer"})

    def _stock(self, qty):
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, qty
        )

    def _order(self, qty=1.0):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": qty})
                ],
            }
        )

    def _user(self, login, xmlids):
        groups = [self.env.ref("base.group_user").id]
        groups.append(self.env.ref("sales_team.group_sale_salesman").id)
        groups += [self.env.ref(x).id for x in xmlids]
        return (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": "%s@example.com" % login,
                    "groups_id": [(6, 0, groups)],
                }
            )
        )

    def _visible_line_fields(self, user):
        """Names of the quantity fields visible in the order line form."""
        arch = self.env["sale.order"].with_user(user).get_view(view_type="form")["arch"]
        tree = etree.fromstring(arch)
        visible = set()
        for name in QTY_GROUPS:
            for node in tree.xpath(
                "//field[@name='order_line']/form//field[@name='%s']" % name
            ):
                modifiers = json.loads(node.get("modifiers") or "{}")
                if modifiers.get("invisible") is not True:
                    visible.add(name)
        return visible

    def test_free_qty_follows_product(self):
        """
        Given a storable product with 5 units on hand
        When a sale order line is created for it
        Then the line free_qty mirrors the product free quantity
        """
        self._stock(5.0)
        line = self._order().order_line
        self.assertEqual(line.free_qty, 5.0)
        self.assertEqual(line.free_qty, self.product.free_qty)

    def test_free_qty_discounts_reservations(self):
        """
        Given 5 units on hand and 3 of them reserved by a confirmed order
        When another order line is read
        Then free_qty is 2 while the product still has 5 on hand
        """
        self._stock(5.0)
        first = self._order(qty=3.0)
        first.action_confirm()
        picking = first.picking_ids
        picking.action_assign()
        second = self._order(qty=1.0).order_line
        self.assertEqual(self.product.qty_available, 5.0)
        self.assertEqual(second.free_qty, 2.0)

    def test_free_qty_updates_with_stock(self):
        """
        Given a line created with no stock
        When 4 units are received afterwards
        Then free_qty is updated through the related field
        """
        line = self._order().order_line
        self.assertEqual(line.free_qty, 0.0)
        self._stock(4.0)
        self.env.invalidate_all()
        self.assertEqual(line.free_qty, 4.0)

    def test_settings_enable_and_disable_groups(self):
        """
        Given the settings screen
        When the free quantity option is enabled and then disabled
        Then the group is implied to internal users and later removed
        """
        user_group = self.env.ref("base.group_user")
        group = self.env.ref(QTY_GROUPS["free_qty"])
        settings = self.env["res.config.settings"].create({"group_free_qty": True})
        settings.execute()
        self.assertIn(group, user_group.implied_ids)
        settings = self.env["res.config.settings"].create({"group_free_qty": False})
        settings.execute()
        self.assertNotIn(group, user_group.implied_ids)

    def test_settings_expose_each_option(self):
        """
        Given the settings model
        When the three quantity options are enabled
        Then each one maps to its own implied group
        """
        settings = self.env["res.config.settings"].create(
            {
                "group_qty_available_today": True,
                "group_free_qty_today": True,
                "group_free_qty": True,
            }
        )
        settings.execute()
        user_group = self.env.ref("base.group_user")
        for xmlid in QTY_GROUPS.values():
            self.assertIn(self.env.ref(xmlid), user_group.implied_ids)

    def test_fields_hidden_without_groups(self):
        """
        Given a salesman without any quantity group
        When the order form is rendered
        Then none of the three quantity fields is in the line form
        """
        self.assertEqual(self._visible_line_fields(self._user("qty_plain", [])), set())

    def test_each_group_reveals_only_its_field(self):
        """
        Given salesmen that belong to one quantity group each
        When the order form is rendered for each of them
        Then only the field tied to their group is shown
        """
        for name, xmlid in QTY_GROUPS.items():
            visible = self._visible_line_fields(self._user("qty_%s" % name, [xmlid]))
            self.assertEqual(visible, {name})
