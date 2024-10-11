from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    counterpart_picking_id = fields.Many2one(
        "stock.picking", string="Counterpart Picking", copy=False
    )

    def action_confirm(self):
        res = super(StockPicking, self).action_confirm()
        for picking in self:
            if (
                picking.picking_type_id.code == "incoming"
                and picking.partner_id.is_company
            ):
                inter_company_partner = (
                    self.env["res.company"]
                    .sudo()
                    .search([("partner_id", "=", picking.partner_id.id)], limit=1)
                )

                if inter_company_partner:
                    counterpart_picking = picking._create_outgoing_counterpart_picking(
                        inter_company_partner
                    )
                    picking.counterpart_picking_id = counterpart_picking
            elif (
                picking.picking_type_id.code == "outgoing"
                and picking.partner_id.is_company
            ):
                inter_company_partner = (
                    self.env["res.company"]
                    .sudo()
                    .search([("partner_id", "=", picking.partner_id.id)], limit=1)
                )

                if inter_company_partner:
                    counterpart_picking = picking._create_incoming_counterpart_picking(
                        inter_company_partner
                    )
                    picking.counterpart_picking_id = counterpart_picking

        return res

    def _create_outgoing_counterpart_picking(self, company):
        """
        Cria o picking de entrega na empresa destino e retorna o registro criado.
        """
        vals = self._get_counterpart_picking_vals(company)
        outgoing_picking = (
            self.env["stock.picking"].sudo().with_company(company).create(vals)
        )

        return outgoing_picking

    def _create_incoming_counterpart_picking(self, company):
        """
        Cria o picking de recebimento na empresa destino e retorna o registro criado.
        """
        vals = self._get_counterpart_picking_vals(company, incoming=True)
        incoming_picking = (
            self.env["stock.picking"].sudo().with_company(company).create(vals)
        )
        return incoming_picking

    def _get_counterpart_picking_vals(self, company, incoming=False):
        """
        Obtém os valores para criar o picking de entrega ou recebimento.
        """
        warehouse = company.intercompany_out_type_id.warehouse_id
        if incoming:
            return {
                "partner_id": self.env.user.company_id.partner_id.id,
                "company_id": company.id,
                "origin": self.name,
                "picking_type_id": company.intercompany_in_type_id.id,
                "state": "draft",
                "location_id": self.env.ref("stock.stock_location_customers").id,
                "location_dest_id": warehouse.lot_stock_id.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "product_uom_qty": line.product_uom_qty,
                            "product_uom": line.product_uom.id,
                            "name": line.name,
                            "location_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                            "location_dest_id": warehouse.lot_stock_id.id,
                        },
                    )
                    for line in self.move_ids
                ],
            }
        else:
            return {
                "partner_id": self.env.user.company_id.partner_id.id,
                "company_id": company.id,
                "origin": self.name,
                "picking_type_id": company.intercompany_out_type_id.id,
                "state": "draft",
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "product_uom_qty": line.product_uom_qty,
                            "product_uom": line.product_uom.id,
                            "name": line.name,
                            "location_id": warehouse.lot_stock_id.id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        },
                    )
                    for line in self.move_ids
                ],
            }

    def action_cancel(self):
        """
        Sobrescreve o método action_cancel para cancelar também o picking
        correspondente intercompany.
        """
        for picking in self:
            if picking.counterpart_picking_id:
                picking.counterpart_picking_id.sudo().action_cancel()
        return super(StockPicking, self).action_cancel()
