from odoo import Command, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_fill_from_nfe(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Preencher por NF-e"),
            "res_model": "stock.picking.fill.nfe",
            "view_mode": "form",
            "target": "new",
            "context": {"default_picking_id": self.id},
        }

    def _fill_from_nfe(self, document):
        """Liga cada linha da NF-e a um movimento do mesmo produto (criando-o
        se faltar) e propõe um lote para produtos rastreados por lote."""
        self.ensure_one()
        linked = self.move_ids.origin_nfe_line_id
        for line in document.fiscal_line_ids.filtered("product_id"):
            if line in linked:
                continue
            product = line.product_id
            move = fields.first(
                self.move_ids.filtered(
                    lambda m, product=product: m.product_id == product
                    and not m.origin_nfe_line_id
                )
            )
            qty = line.uom_id._compute_quantity(
                line.quantity, move.product_uom if move else product.uom_id
            )
            vals = {
                "origin_nfe_id": document.id,
                "origin_nfe_line_id": line.id,
                "product_uom_qty": qty,
            }
            if move:
                move.write(vals)
            else:
                move = self.env["stock.move"].create(
                    dict(
                        vals,
                        name=line.name or product.display_name,
                        picking_id=self.id,
                        product_id=product.id,
                        product_uom=product.uom_id.id,
                        location_id=self.location_id.id,
                        location_dest_id=self.location_dest_id.id,
                    )
                )
            linked |= line
            if product.tracking == "lot":
                self._propose_lot_from_nfe(move, line)
        return True

    def _propose_lot_from_nfe(self, move, line):
        lot = (
            self.env["stock.lot"]
            .with_context(default_origin_picking_id=self.id)
            .create(
                {
                    "name": f"{line.document_id.document_number}-{line.id}",
                    "product_id": move.product_id.id,
                    "company_id": move.company_id.id,
                }
            )
        )
        move.write(
            {
                "move_line_ids": [
                    Command.create(
                        {
                            "product_id": move.product_id.id,
                            "lot_id": lot.id,
                            "quantity": move.product_uom_qty,
                            "product_uom_id": move.product_uom.id,
                            "location_id": move.location_id.id,
                            "location_dest_id": move.location_dest_id.id,
                        }
                    )
                ]
            }
        )
