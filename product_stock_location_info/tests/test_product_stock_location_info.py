# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductStockLocationInfo(TransactionCase):
    def test_main_and_alternative_location(self):
        product = self.env["product.template"].create(
            {
                "name": "Produto",
                "type": "consu",
                "is_storable": True,
                "stock": "Almoxarifado",
                "posx": "A",
                "second_stock": "Anexo",
                "second_nivel": "3",
            }
        )
        self.assertEqual(product.posx, "A")
        self.assertEqual(product.second_nivel, "3")
        found = self.env["product.template"].search([("second_stock", "=", "Anexo")])
        self.assertIn(product, found)
