from odoo import fields, models

CONSIGNMENT_FIELDS = {"return_quantity", "consignment_picking_id"}


class StockQuant(models.Model):
    _inherit = "stock.quant"

    return_quantity = fields.Float(string="Quantidade a devolver", copy=False)
    consignment_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Separação da devolução",
        copy=False,
        index="btree_not_null",
    )

    def button_add_to_consignment_return(self):
        picking = self.env["stock.picking"].browse(
            self.env.context.get("default_picking_id")
        )
        if picking:
            for quant in self:
                quant.write(
                    {
                        "return_quantity": quant.available_quantity,
                        "consignment_picking_id": picking.id,
                    }
                )

    def button_remove_from_consignment_return(self):
        self.write({"return_quantity": 0, "consignment_picking_id": False})

    def write(self, vals):
        # a seleção da devolução não exige permissão de ajuste de estoque
        if vals and set(vals) <= CONSIGNMENT_FIELDS:
            self = self.sudo()
        return super().write(vals)
