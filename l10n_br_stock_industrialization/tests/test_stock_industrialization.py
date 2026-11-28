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

    def _delivery(self):
        return self.env["stock.picking"].create(
            {
                "picking_type_id": self.env.ref("stock.warehouse0").out_type_id.id,
                "location_id": self.env.ref("stock.stock_location_output").id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "partner_id": self.partner.id,
                "sale_id": self.sale.id,
            }
        )

    def _consignment_setup(self):
        """Material do cliente em estoque e a separação que o devolve."""
        document = self.env.ref("l10n_br_stock_lot_nfe.nfe_entrada_demo")
        product = self.env.ref("l10n_br_stock_lot_nfe.product_cabo_aco")
        picking = self._receive(product)
        lot = self._set_lot(
            picking,
            "LT-CABO-002",
            origin_nfe_id=document.id,
            origin_nfe_line_id=document.fiscal_line_ids.id,
        )
        picking.button_validate()
        warehouse = self.env.ref("stock.warehouse0")
        pick = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.int_type_id.id,
                "location_id": self.env.ref("stock.stock_location_stock").id,
                "location_dest_id": self.env.ref("stock.stock_location_output").id,
                "partner_id": self.partner.id,
                "fiscal_operation_id": self.service_operation.id,
                "sale_id": self.sale.id,
            }
        )
        quant = pick.consignment_line_ids.filtered(lambda q: q.lot_id == lot)
        quant.with_context(
            default_picking_id=pick.id
        ).button_add_to_consignment_return()
        return pick, quant, lot

    # venda

    def test_sale_counts_split_receipts_from_deliveries(self):
        picking = self._receive(self.product)
        delivery = self._delivery()
        self.sale.invalidate_recordset()
        self.assertEqual(self.sale.industrialization_count, 1)
        self.assertEqual(self.sale.delivery_count, 1)
        action = self.sale.action_view_industrialization()
        self.assertEqual(action["res_id"], picking.id)
        action = self.sale.action_view_delivery()
        self.assertEqual(action["res_id"], delivery.id)

    def test_sale_action_create_industrialization(self):
        action = self.sale.action_create_industrialization()
        self.assertEqual(action["res_model"], "stock.industrialization.create")
        self.assertEqual(action["context"], {"default_sale_id": self.sale.id})

    def test_sale_with_open_receipt_cannot_be_cancelled(self):
        self.sale.action_confirm()
        picking = self._receive(self.product)
        with self.assertRaisesRegex(UserError, "recebimentos para industrialização"):
            self.sale._action_cancel()
        picking.action_cancel()
        self.sale._action_cancel()
        self.assertEqual(self.sale.state, "cancel")

    def test_sale_line_applied_product_sets_product(self):
        line = self.sale.order_line
        line.applied_product_id = self.product
        line._onchange_applied_product_id()
        self.assertEqual(line.product_id, self.product)

    # lote

    def test_lot_price_without_origin_note_is_product_cost(self):
        lot = self.env["stock.lot"].create(
            {
                "name": "LT-SEM-NOTA",
                "product_id": self.product.id,
                "company_id": self.env.company.id,
            }
        )
        self.product.standard_price = 12.5
        self.assertEqual(
            lot._get_origin_unit_price(self.product, self.product.uom_id), 12.5
        )

    # movimento

    def test_route_ids_from_commands(self):
        route_ids = self.env["stock.move"]._route_ids_from_commands(
            {
                "route_ids": [
                    (4, 5),
                    (6, 0, [7, 8]),
                    (1, 9, {}),
                    (3, 11),
                    (4,),
                    42,
                ]
            }
        )
        self.assertEqual(route_ids, [5, 7, 8, 9])
        self.assertEqual(self.env["stock.move"]._route_ids_from_commands({}), [])

    def test_move_merge_follows_the_picking_setting(self):
        wizard = self.env["stock.industrialization.create"].create(
            {
                "sale_id": self.sale.id,
                "line_ids": [
                    Command.create({"product_id": self.product.id, "quantity": 2}),
                    Command.create({"product_id": self.product.id, "quantity": 3}),
                ],
            }
        )
        picking = self.env["stock.picking"].browse(wizard.action_create()["res_id"])
        self.assertTrue(picking.merge_moves)
        picking.merge_moves = False
        picking.action_confirm()
        self.assertEqual(len(picking.move_ids), 2)

    def test_pending_consignment_return_can_be_removed(self):
        pick, quant, _lot = self._consignment_setup()
        delivery = self._delivery()
        pick.action_create_consignment_return()
        move = pick.move_ids
        delivery_move = delivery.move_ids
        self.assertTrue(move.is_consignment_return)
        self.assertTrue(move.move_line_ids)
        self.assertEqual(delivery_move.move_orig_ids, move)
        move.unlink()
        self.assertFalse(move.exists())
        self.assertFalse(delivery_move.exists())
        self.assertFalse(pick.move_ids)

    # separação

    def test_set_sale_blocked_when_receipt_has_sale(self):
        picking = self._receive(self.product)
        with self.assertRaisesRegex(UserError, "já possui uma venda"):
            picking.action_set_sale()

    def test_set_sale_action(self):
        picking = self._receive(self.product)
        picking.sale_id = False
        action = picking.action_set_sale()
        self.assertEqual(action["res_model"], "stock.industrialization.set.sale")

    def test_consignment_return_operation_must_be_service(self):
        pick, _quant, _lot = self._consignment_setup()
        self.assertEqual(
            pick._consignment_return_operation()[0],
            self.env.ref(f"{MODULE}.fo_retorno_industrializacao"),
        )
        pick.fiscal_operation_id = self.env.ref("l10n_br_fiscal.fo_venda")
        with self.assertRaisesRegex(UserError, "exige a operação de serviço"):
            pick._consignment_return_operation()

    def test_consignment_return_of_finished_picking(self):
        pick, _quant, _lot = self._consignment_setup()
        pick.state = "done"
        with self.assertRaisesRegex(UserError, "concluída ou cancelada"):
            pick.action_create_consignment_return()

    def test_consignment_return_needs_open_delivery(self):
        pick, _quant, _lot = self._consignment_setup()
        with self.assertRaisesRegex(UserError, "não tem entrega em aberto"):
            pick.action_create_consignment_return()

    def test_consignment_return_quantity_limits(self):
        pick, quant, _lot = self._consignment_setup()
        self._delivery()
        quant.return_quantity = 0
        with self.assertRaisesRegex(UserError, "maior que zero"):
            pick.action_create_consignment_return()
        quant.return_quantity = quant.available_quantity + 1
        with self.assertRaisesRegex(UserError, "maior que zero"):
            pick.action_create_consignment_return()

    def test_consignment_return_owner_must_belong_to_the_partner(self):
        pick, _quant, _lot = self._consignment_setup()
        self._delivery()
        pick.action_create_consignment_return()
        line = pick.move_ids.move_line_ids
        line.owner_id = self.env["res.partner"].create({"name": "Outro dono"})
        with self.assertRaisesRegex(UserError, "não pertence ao parceiro"):
            pick._check_owner_for_consignment_return()

    def test_receipt_cannot_repeat_product_and_lot(self):
        picking = self._receive(self.product)
        self._set_lot(picking, "LT-REPETIDO")
        line = picking.move_ids.move_line_ids
        line.copy({"quantity": 1})
        with self.assertRaisesRegex(UserError, "mesmo produto e lote"):
            picking._check_lots_for_industrialization()

    # assistentes

    def test_create_wizard_needs_quantity(self):
        wizard = self.env["stock.industrialization.create"].create(
            {
                "sale_id": self.sale.id,
                "line_ids": [
                    Command.create({"product_id": self.product.id, "quantity": 0})
                ],
            }
        )
        with self.assertRaisesRegex(UserError, "ao menos um insumo"):
            wizard.action_create()

    def test_create_wizard_needs_picking_type(self):
        self.env["stock.picking.type"].search(
            [("is_industrialization", "=", True)]
        ).write({"is_industrialization": False})
        wizard = self.env["stock.industrialization.create"].create(
            {
                "sale_id": self.sale.id,
                "line_ids": [
                    Command.create({"product_id": self.product.id, "quantity": 1})
                ],
            }
        )
        with self.assertRaisesRegex(UserError, "tipo de operação de recebimento"):
            wizard.action_create()

    def _set_sale_wizard(self, picking, **vals):
        wizard_model = self.env["stock.industrialization.set.sale"].with_context(
            active_id=picking.id
        )
        values = wizard_model.default_get(list(wizard_model._fields))
        return wizard_model.create(dict(values, **vals))

    def test_set_sale_wizard_needs_partner(self):
        picking = self._receive(self.product)
        picking.partner_id = False
        with self.assertRaisesRegex(UserError, "precisa de um parceiro"):
            self._set_sale_wizard(picking)

    def test_set_sale_wizard_assigns_sale(self):
        self.sale.action_confirm()
        picking = self._receive(self.product)
        picking.write({"sale_id": False, "group_id": False, "origin": False})
        wizard = self._set_sale_wizard(picking, sale_id=self.sale.id)
        result = wizard.action_set_sale()
        self.assertEqual(result["type"], "ir.actions.act_window_close")
        self.assertEqual(picking.sale_id, self.sale)
        self.assertEqual(picking.origin, self.sale.name)

    def test_set_sale_wizard_posts_origin_to_received_lots(self):
        self.sale.action_confirm()
        picking = self._receive(self.product)
        picking.write({"sale_id": False, "group_id": False})
        lot = self._set_lot(picking, "LT-ALU-002")
        picking.button_validate()
        self.assertFalse(lot.origin_sale_id)
        wizard = self._set_sale_wizard(picking, sale_id=self.sale.id)
        wizard.action_set_sale()
        self.assertEqual(lot.origin_sale_id, self.sale)

    def test_set_sale_wizard_customer_must_match(self):
        picking = self._receive(self.product)
        other = self.env["res.partner"].create({"name": "Outro cliente"})
        other_sale = self.env["sale.order"].create({"partner_id": other.id})
        wizard = self._set_sale_wizard(picking, sale_id=other_sale.id)
        with self.assertRaisesRegex(UserError, "cliente do pedido é diferente"):
            wizard.action_set_sale()
