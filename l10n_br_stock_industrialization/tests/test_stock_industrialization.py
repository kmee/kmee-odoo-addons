from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

MODULE = "l10n_br_stock_industrialization"


@tagged("post_install", "-at_install")
class TestStockIndustrialization(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env.ref("l10n_br_base.res_partner_cliente1_sp")
        cls.service_operation = cls.env.ref(f"{MODULE}.fo_servico_industrializacao")
        cls.route = cls.env.ref(f"{MODULE}.route_apenas_cobranca")
        cls.product = cls.env.ref(f"{MODULE}.product_perfil_aluminio")
        cls.service = cls.env.ref(f"{MODULE}.product_servico_usinagem")
        cls.plain_product = cls.env["product.product"].create(
            {
                "name": "Bucha de Nylon 12 mm",
                "type": "consu",
                "is_storable": True,
            }
        )
        cls.sale = cls._create_sale(cls.service_operation, cls.service)

    @classmethod
    def _create_sale(cls, operation, product, **line_vals):
        return cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "fiscal_operation_id": operation.id,
                "order_line": [
                    Command.create(
                        dict(
                            product_id=product.id,
                            product_uom_qty=1,
                            price_unit=100,
                            **line_vals,
                        )
                    )
                ],
            }
        )

    def _receive(self, product, qty=10, sale=None):
        wizard = self.env["stock.industrialization.create"].create(
            {
                "sale_id": (sale or self.sale).id,
                "line_ids": [
                    Command.create({"product_id": product.id, "quantity": qty})
                ],
            }
        )
        return self.env["stock.picking"].browse(wizard.action_create()["res_id"])

    def _set_lot(self, picking, name, **lot_vals):
        picking.action_confirm()
        move = picking.move_ids
        lot = self.env["stock.lot"].create(
            dict(
                name=name,
                product_id=move.product_id.id,
                company_id=picking.company_id.id,
                **lot_vals,
            )
        )
        move.move_line_ids.unlink()
        move.move_line_ids = [
            Command.create(
                {
                    "picking_id": picking.id,
                    "product_id": move.product_id.id,
                    "lot_id": lot.id,
                    "quantity": move.product_uom_qty,
                    "product_uom_id": move.product_uom.id,
                    "location_id": move.location_id.id,
                    "location_dest_id": move.location_dest_id.id,
                    "picked": True,
                }
            )
        ]
        return lot

    def test_receipt_has_owner_and_operation(self):
        self.sale.action_confirm()
        picking = self._receive(self.product)
        self.assertTrue(picking.is_industrialization)
        self.assertEqual(
            picking.picking_type_id,
            self.env.ref(f"{MODULE}.picking_type_industrialization_in"),
        )
        self.assertEqual(
            picking.fiscal_operation_id,
            self.env.ref("l10n_br_fiscal.fo_entrada_industrializacao"),
        )
        self.assertEqual(picking.owner_id, self.partner)
        self.assertEqual(picking.sale_id, self.sale)
        self.assertEqual(self.sale.industrialization_ids, picking)

    def test_lot_is_required(self):
        picking = self._receive(self.plain_product)
        picking.action_confirm()
        picking.move_ids.quantity = 10
        picking.move_ids.picked = True
        with self.assertRaisesRegex(UserError, "precisa de lote"):
            picking.button_validate()

    def test_lots_reserved_to_sale_and_owned_by_customer(self):
        self.sale.action_confirm()
        picking = self._receive(self.product)
        lot = self._set_lot(picking, "LT-ALU-001")
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(lot.origin_sale_id, self.sale)
        quant = self.env["stock.quant"].search([("lot_id", "=", lot.id)])
        self.assertEqual(
            quant.filtered(lambda q: q.location_id.usage == "internal").owner_id,
            self.partner,
        )

    def test_consignment_return_uses_origin_note_price(self):
        document = self.env.ref("l10n_br_stock_lot_nfe.nfe_entrada_demo")
        product = self.env.ref("l10n_br_stock_lot_nfe.product_cabo_aco")
        picking = self._receive(product)
        lot = self._set_lot(
            picking,
            "LT-CABO-001",
            origin_nfe_id=document.id,
            origin_nfe_line_id=document.fiscal_line_ids.id,
        )
        picking.button_validate()

        stock = self.env.ref("stock.stock_location_stock")
        output = self.env.ref("stock.stock_location_output")
        warehouse = self.env.ref("stock.warehouse0")
        pick = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.int_type_id.id,
                "location_id": stock.id,
                "location_dest_id": output.id,
                "partner_id": self.partner.id,
                "fiscal_operation_id": self.service_operation.id,
                "sale_id": self.sale.id,
            }
        )
        delivery = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.out_type_id.id,
                "location_id": output.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "partner_id": self.partner.id,
                "sale_id": self.sale.id,
            }
        )
        self.assertTrue(pick.display_consignment_page)
        quant = pick.consignment_line_ids.filtered(lambda q: q.lot_id == lot)
        self.assertEqual(len(quant), 1)
        quant.with_context(
            default_picking_id=pick.id
        ).button_add_to_consignment_return()
        self.assertEqual(pick.to_return_consignment_line_ids, quant)

        pick.action_create_consignment_return()

        move = pick.move_ids
        self.assertTrue(move.is_consignment_return)
        self.assertEqual(move.price_unit, 85)
        self.assertEqual(move.move_line_ids.owner_id, self.partner)
        self.assertEqual(move.move_line_ids.lot_id, lot)
        delivery_move = delivery.move_ids
        self.assertEqual(delivery_move.price_unit, 85)
        self.assertEqual(
            delivery_move.fiscal_operation_line_id,
            self.env.ref(f"{MODULE}.fo_retorno_industrializacao_retorno_nao_utilizado"),
        )
        self.assertFalse(pick.to_return_consignment_line_ids)

        move.move_line_ids.owner_id = False
        with self.assertRaisesRegex(UserError, "exigem dono"):
            pick._check_owner_for_consignment_return()

    def test_billing_only_route_needs_service_operation(self):
        sale = self._create_sale(self.env.ref("l10n_br_fiscal.fo_venda"), self.product)
        with self.assertRaises(ValidationError):
            sale.order_line.route_id = self.route
        sale.fiscal_operation_id = self.service_operation
        sale.order_line.route_id = self.route
        sale.order_line.applied_product_id = self.product
        sale.action_confirm()
        self.assertFalse(sale.picking_ids)
        self.assertFalse(
            self.env["stock.move"].search([("sale_line_id", "in", sale.order_line.ids)])
        )
