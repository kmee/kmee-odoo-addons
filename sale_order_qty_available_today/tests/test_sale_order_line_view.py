from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderLineView(TransactionCase):
    def test_qty_available_today_in_line_form(self):
        """O campo qty_available_today aparece no formulário da linha."""
        arch = self.env["sale.order"].get_view(
            self.env.ref("sale.view_order_form").id, "form"
        )["arch"]
        tree = etree.fromstring(arch)
        fields = tree.xpath(
            "//field[@name='order_line']/form//field[@name='qty_available_today']"
        )
        self.assertTrue(fields)
