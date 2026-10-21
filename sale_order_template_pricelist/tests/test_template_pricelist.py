# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderTemplatePricelist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        # make the pricelist and template fields visible in the sale order form
        cls.env.user.write(
            {
                "group_ids": [
                    (4, cls.env.ref("product.group_product_pricelist").id),
                    (4, cls.env.ref("sale_management.group_sale_order_template").id),
                ]
            }
        )
        Pricelist = cls.env["product.pricelist"]
        cls.pricelist_customer = Pricelist.create({"name": "Customer pricelist"})
        cls.pricelist_campaign = Pricelist.create({"name": "Black Friday"})
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Customer",
                "property_product_pricelist": cls.pricelist_customer.id,
            }
        )
        cls.template_campaign = cls.env["sale.order.template"].create(
            {"name": "Black Friday", "pricelist_id": cls.pricelist_campaign.id}
        )
        cls.template_plain = cls.env["sale.order.template"].create(
            {"name": "Plain template"}
        )

    def test_template_stores_pricelist(self):
        """
        Given a quotation template created with a pricelist
        When we read it back
        Then the pricelist is kept and templates without one have it empty
        """
        self.assertEqual(self.template_campaign.pricelist_id, self.pricelist_campaign)
        self.assertFalse(self.template_plain.pricelist_id)

    def test_template_pricelist_overrides_customer_pricelist(self):
        """
        Given a customer whose default pricelist is not the campaign one
        When the quotation template with a pricelist is selected on the order
        Then the order pricelist becomes the template pricelist
        """
        form = Form(self.env["sale.order"])
        form.partner_id = self.partner
        self.assertEqual(form.pricelist_id, self.pricelist_customer)
        form.sale_order_template_id = self.template_campaign
        self.assertEqual(form.pricelist_id, self.pricelist_campaign)
        order = form.save()
        self.assertEqual(order.pricelist_id, self.pricelist_campaign)

    def test_template_without_pricelist_keeps_customer_pricelist(self):
        """
        Given a template that has no pricelist
        When it is selected on an order of a customer with a pricelist
        Then the customer pricelist is kept
        """
        with Form(self.env["sale.order"]) as form:
            form.partner_id = self.partner
            form.sale_order_template_id = self.template_plain
            self.assertEqual(form.pricelist_id, self.pricelist_customer)

    def test_clearing_template_does_not_reset_pricelist(self):
        """
        Given an order that got the campaign pricelist from its template
        When the template is removed from the order
        Then the order keeps the pricelist it already had
        """
        with Form(self.env["sale.order"]) as form:
            form.partner_id = self.partner
            form.sale_order_template_id = self.template_campaign
            form.sale_order_template_id = self.env["sale.order.template"]
            self.assertEqual(form.pricelist_id, self.pricelist_campaign)

    def test_onchange_method_on_recordset(self):
        """
        Given a recordset with one order with and one order without template
        When the onchange method runs on the whole recordset
        Then only the order whose template carries a pricelist is changed
        """
        Order = self.env["sale.order"]
        with_tpl = Order.new(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist_customer.id,
                "sale_order_template_id": self.template_campaign.id,
            }
        )
        without_tpl = Order.new(
            {"partner_id": self.partner.id, "pricelist_id": self.pricelist_customer.id}
        )
        (with_tpl | without_tpl)._onchange_sale_order_template_id_pricelist_sync()
        self.assertEqual(with_tpl.pricelist_id, self.pricelist_campaign)
        self.assertEqual(without_tpl.pricelist_id, self.pricelist_customer)

    def test_template_form_shows_pricelist_field(self):
        """
        Given the quotation template form view
        When the view is loaded
        Then the pricelist field is in the sale_info group
        """
        arch = self.env["sale.order.template"].get_view(
            self.env.ref("sale_management.sale_order_template_view_form").id, "form"
        )["arch"]
        nodes = etree.fromstring(arch).xpath(
            "//group[@name='sale_info']//field[@name='pricelist_id']"
        )
        self.assertEqual(len(nodes), 1)
