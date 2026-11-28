from odoo import api, fields, models
from odoo.exceptions import UserError


class StockIndustrializationSetSale(models.TransientModel):
    _name = "stock.industrialization.set.sale"
    _description = "Atribuir recebimento a uma venda"

    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        related="picking_id.partner_id",
        string="Cliente",
    )
    sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Pedido de venda",
        required=True,
        domain="[('partner_id', '=', partner_id), ('state', '=', 'sale')]",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        picking = self.env["stock.picking"].browse(self.env.context.get("active_id"))
        if not picking.partner_id:
            raise UserError(
                self.env._("O recebimento precisa de um parceiro para ser atribuído.")
            )
        res["picking_id"] = picking.id
        return res

    def action_set_sale(self):
        self.ensure_one()
        if self.sale_id.partner_id != self.partner_id:
            raise UserError(
                self.env._("O cliente do pedido é diferente do cliente do recebimento.")
            )
        picking = self.picking_id
        picking.write(
            {
                "origin": self.sale_id.name,
                "group_id": self.sale_id.procurement_group_id.id,
                "sale_id": self.sale_id.id,
            }
        )
        if picking.state == "done":
            picking._set_lots_origin_sale()
        return {"type": "ir.actions.act_window_close"}
