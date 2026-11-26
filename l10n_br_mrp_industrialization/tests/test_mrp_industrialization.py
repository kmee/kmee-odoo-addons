from odoo import Command
from odoo.tests import TransactionCase, tagged

MODULE = "l10n_br_stock_industrialization"


@tagged("post_install", "-at_install")
class TestMrpIndustrialization(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env.ref("l10n_br_base.res_partner_cliente1_sp")
        cls.operation = cls.env.ref(f"{MODULE}.fo_servico_industrializacao")
        cls.operation.journal_id = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.env.company.id)], limit=1
        )
        stock = cls.env.ref("stock.stock_location_stock")
        customers = cls.env.ref("stock.stock_location_customers")

        cls.customer_product = cls.env.ref("l10n_br_stock_lot_nfe.product_cabo_aco")
        cls.applied_product = cls._create_product("Bucha de Nylon 12 mm")
        cls.finished_product = cls._create_product("Suporte de Cabo Usinado")
        document = cls.env.ref("l10n_br_stock_lot_nfe.nfe_entrada_demo")
        cls.lot = cls.env["stock.lot"].create(
            {
                "name": "LT-CABO-IND-01",
                "product_id": cls.customer_product.id,
                "origin_nfe_id": document.id,
                "origin_nfe_line_id": document.fiscal_line_ids.id,
            }
        )
        quants = cls.env["stock.quant"]
        quants._update_available_quantity(
            cls.customer_product, stock, 10, lot_id=cls.lot, owner_id=cls.partner
        )
        quants._update_available_quantity(cls.applied_product, stock, 50)

        bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.finished_product.product_tmpl_id.id,
                "bom_line_ids": [
                    Command.create(
                        {"product_id": cls.customer_product.id, "product_qty": 2}
                    ),
                    Command.create(
                        {"product_id": cls.applied_product.id, "product_qty": 4}
                    ),
                ],
            }
        )
        production = cls.env["mrp.production"].create(
            {
                "product_id": cls.finished_product.id,
                "bom_id": bom.id,
                "product_qty": 3,
            }
        )
        production.action_confirm()
        for raw in production.move_raw_ids:
            raw.move_line_ids.unlink()
            is_customer = raw.product_id == cls.customer_product
            raw.move_line_ids = [
                Command.create(
                    {
                        "product_id": raw.product_id.id,
                        "product_uom_id": raw.product_uom.id,
                        "quantity": raw.product_uom_qty,
                        "lot_id": cls.lot.id if is_customer else False,
                        "owner_id": cls.partner.id if is_customer else False,
                        "location_id": stock.id,
                        "location_dest_id": raw.location_dest_id.id,
                        "picked": True,
                    }
                )
            ]
        production.qty_producing = 3
        production.button_mark_done()
        cls.production = production

        cls.sale = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "fiscal_operation_id": cls.operation.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": cls.finished_product.id,
                            "product_uom_qty": 3,
                            "price_unit": 38,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.applied_product.id,
                            "product_uom_qty": 12,
                            "price_unit": 12.5,
                            "route_id": cls.env.ref(
                                f"{MODULE}.route_apenas_cobranca"
                            ).id,
                        }
                    ),
                ],
            }
        )
        cls.picking = cls.env["stock.picking"].create(
            {
                "partner_id": cls.partner.id,
                "picking_type_id": cls.env.ref("stock.picking_type_out").id,
                "location_id": stock.id,
                "location_dest_id": customers.id,
                "fiscal_operation_id": cls.operation.id,
                "invoice_state": "2binvoiced",
                "sale_id": cls.sale.id,
                "move_ids": [
                    Command.create(
                        {
                            "name": cls.finished_product.name,
                            "product_id": cls.finished_product.id,
                            "product_uom_qty": 3,
                            "product_uom": cls.finished_product.uom_id.id,
                            "location_id": stock.id,
                            "location_dest_id": customers.id,
                            "invoice_state": "2binvoiced",
                            "sale_line_id": cls.sale.order_line[0].id,
                            "fiscal_operation_id": cls.operation.id,
                            "move_orig_ids": [
                                Command.link(production.move_finished_ids.id)
                            ],
                        }
                    )
                ],
            }
        )
        cls.picking.action_confirm()
        cls.picking.action_assign()
        cls.picking.move_ids.picked = True
        cls.picking._action_done()

    @classmethod
    def _create_product(cls, name):
        return cls.env["product.product"].create(
            {
                "name": name,
                "type": "consu",
                "is_storable": True,
                "standard_price": 5,
                "list_price": 20,
            }
        )

    def _invoice(self):
        wizard = (
            self.env["stock.invoice.onshipping"]
            .with_context(active_ids=self.picking.ids, active_model="stock.picking")
            .create({})
        )
        return wizard._action_generate_invoices()

    def _line(self, invoice, product):
        return invoice.invoice_line_ids.filtered(
            lambda line: line.product_id == product
        )

    def test_invoice_from_production(self):
        invoice = self._invoice()
        returned = self._line(invoice, self.customer_product)
        self.assertEqual(len(returned), 1)
        self.assertEqual(returned.quantity, 6)
        self.assertEqual(returned.price_unit, 85)
        self.assertEqual(
            returned.fiscal_operation_line_id,
            self.env.ref(f"{MODULE}.fo_retorno_industrializacao_retorno_utilizado"),
        )
        service = self._line(invoice, self.applied_product)
        self.assertEqual(len(service), 1)
        self.assertEqual(service.quantity, 12)
        self.assertEqual(service.price_unit, 12.5)
        self.assertEqual(
            service.fiscal_operation_line_id,
            self.env.ref(f"{MODULE}.fol_servico_industrializacao_mat_prima"),
        )

    def test_line_tracks_the_production(self):
        invoice = self._invoice()
        returned = self._line(invoice, self.customer_product)
        raw = self.production.move_raw_ids
        self.assertEqual(
            returned.origin_mo_move_line_ids,
            raw.filtered(lambda m: m.product_id == self.customer_product),
        )
        self.assertTrue(all(raw.mapped("has_been_invoiced_industrialization")))
        self.assertEqual(invoice.industrialization_production_ids, self.production)

    def test_cancel_invoice_releases_the_consumption(self):
        invoice = self._invoice()
        self._line(invoice, self.applied_product).unlink()
        invoice.button_cancel()
        self.assertFalse(
            any(
                self.production.move_raw_ids.mapped(
                    "has_been_invoiced_industrialization"
                )
            )
        )
        self.assertEqual(len(self._invoice()), 1)

    def test_delivered_product_line_has_operation_line(self):
        invoice = self._invoice()
        delivered = self._line(invoice, self.finished_product)
        self.assertEqual(
            delivered.fiscal_operation_line_id,
            self.env.ref(f"{MODULE}.fol_servico_industrializacao_prod_acabado"),
        )
        self.assertEqual(delivered.cfop_id.code, "5124")
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
