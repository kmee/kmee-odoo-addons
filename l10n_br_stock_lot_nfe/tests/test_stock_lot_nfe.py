from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStockLotNfe(TransactionCase):
    def setUp(self):
        super().setUp()
        self.product = self.env.ref("l10n_br_stock_lot_nfe.product_cabo_aco")
        self.document = self.env.ref("l10n_br_stock_lot_nfe.nfe_entrada_demo")
        self.picking = self.env.ref("l10n_br_stock_lot_nfe.picking_recebimento_demo")

    def test_lot_name_has_origin_suffix(self):
        lot = self.env["stock.lot"].create(
            {
                "name": "L001",
                "product_id": self.product.id,
                "origin": "PO0001",
                "numero_nota": "1234",
            }
        )
        self.assertEqual(lot.name, "L001 [PO0001]")
        self.assertEqual(lot.simple_name, "L001")
        self.assertEqual(lot.numero_nota, "1234")

    def test_lot_inherits_nfe_from_move(self):
        move = self.picking.move_ids
        move.write(
            {
                "origin_nfe_id": self.document.id,
                "origin_nfe_line_id": self.document.fiscal_line_ids.id,
            }
        )
        lot = (
            self.env["stock.lot"]
            .with_context(default_origin_picking_id=self.picking.id)
            .create({"name": "L002", "product_id": self.product.id})
        )
        self.assertEqual(lot.origin_nfe_id, self.document)
        self.assertEqual(lot.origin_nfe_line_id, self.document.fiscal_line_ids)
        self.assertEqual(lot.numero_nota, self.document.document_number)
        self.assertEqual(lot.origin, self.picking.origin)
        self.assertEqual(lot.name, f"L002 [{self.picking.origin}]")

    def test_invoice_line_values_carry_origin_nfe(self):
        move = self.picking.move_ids
        move.write(
            {
                "origin_nfe_id": self.document.id,
                "origin_nfe_line_id": self.document.fiscal_line_ids.id,
            }
        )
        wizard = self.env["stock.invoice.onshipping"].new({})
        with patch(
            "odoo.addons.l10n_br_stock_account.wizards.stock_invoice_onshipping."
            "StockInvoiceOnshipping._get_invoice_line_values",
            return_value={"name": "linha"},
        ):
            values = wizard._get_invoice_line_values(move, {}, self.env["account.move"])
        self.assertEqual(values["origin_nfe_id"], self.document.id)
        self.assertEqual(values["origin_nfe_line_id"], self.document.fiscal_line_ids.id)

    def test_fill_picking_from_nfe(self):
        self.picking._fill_from_nfe(self.document)
        move = self.picking.move_ids
        self.assertEqual(move.origin_nfe_id, self.document)
        self.assertEqual(move.origin_nfe_line_id, self.document.fiscal_line_ids)
        lot = move.move_line_ids.lot_id
        self.assertEqual(lot.origin_nfe_id, self.document)
        self.assertEqual(lot.numero_nota, self.document.document_number)
