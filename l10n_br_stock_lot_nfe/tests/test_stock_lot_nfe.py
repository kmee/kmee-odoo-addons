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
        # a linha com o lote proposto fica no recebimento (aparece na aba de operações)
        self.assertEqual(move.move_line_ids.picking_id, self.picking)
        self.assertIn(move.move_line_ids, self.picking.move_line_ids)

    def test_document_display_name_for_lot_creation(self):
        document = self.document.with_context(show_name_for_lot_creation=True)
        self.assertEqual(
            document.display_name,
            f"{self.document.partner_id.name} Nota:{self.document.document_number}",
        )

    def test_document_line_display_name_for_lot_creation(self):
        line = self.document.fiscal_line_ids.with_context(
            show_name_for_lot_creation=True
        )
        self.assertEqual(
            line.display_name,
            f"{line.name} Qtd:{line.quantity} Unitário:{line.price_unit}",
        )

    def test_onchange_name_adds_origin(self):
        lot = self.env["stock.lot"].new(
            {"name": "L010", "product_id": self.product.id, "origin": "PO0007"}
        )
        lot._onchange_name_add_origin()
        self.assertEqual(lot.name, "L010 [PO0007]")
        # idempotente: nome que já tem origem não é alterado
        lot._onchange_name_add_origin()
        self.assertEqual(lot.name, "L010 [PO0007]")

    def test_lot_without_matching_move_keeps_nfe_empty(self):
        self.assertFalse(self.picking.move_ids.origin_nfe_id)
        lot = (
            self.env["stock.lot"]
            .with_context(default_origin_picking_id=self.picking.id)
            .create({"name": "L003", "product_id": self.product.id})
        )
        self.assertFalse(lot.origin_nfe_id)
        self.assertFalse(lot.numero_nota)

    def test_fill_is_idempotent_for_linked_lines(self):
        self.picking._fill_from_nfe(self.document)
        moves = self.picking.move_ids
        self.picking._fill_from_nfe(self.document)
        self.assertEqual(self.picking.move_ids, moves)
        self.assertEqual(len(moves.move_line_ids), 1)

    def test_fill_creates_move_when_product_is_missing(self):
        self.picking.move_ids.unlink()
        self.picking._fill_from_nfe(self.document)
        move = self.picking.move_ids
        self.assertEqual(len(move), 1)
        self.assertEqual(move.product_id, self.product)
        self.assertEqual(move.origin_nfe_id, self.document)
        self.assertEqual(move.origin_nfe_line_id, self.document.fiscal_line_ids)
        self.assertEqual(move.location_id, self.picking.location_id)
        self.assertEqual(move.location_dest_id, self.picking.location_dest_id)

    def test_fill_wizard(self):
        action = self.picking.action_fill_from_nfe()
        self.assertEqual(action["res_model"], "stock.picking.fill.nfe")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_picking_id"], self.picking.id)
        wizard = self.env["stock.picking.fill.nfe"].create(
            {"picking_id": self.picking.id, "document_id": self.document.id}
        )
        result = wizard.action_confirm()
        self.assertEqual(result["type"], "ir.actions.act_window_close")
        self.assertEqual(self.picking.move_ids.origin_nfe_id, self.document)
