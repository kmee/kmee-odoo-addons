from odoo import api, fields, models

ORIGIN_SEPARATOR = " ["


class StockLot(models.Model):
    _inherit = "stock.lot"

    numero_nota = fields.Char(string="Número da nota fiscal")
    origin = fields.Char(
        string="Documento de Origem",
        default=lambda self: self._get_default_origin_picking().origin or False,
    )
    origin_purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Compra de origem",
        default=lambda self: self._get_default_origin_order("purchase.order"),
    )
    origin_sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Venda de origem",
        default=lambda self: self._get_default_origin_order("sale.order"),
    )
    origin_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Separação de origem",
        default=lambda self: self._get_default_origin_picking().id or False,
    )
    origin_nfe_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document",
        string="Nota de Origem",
    )
    origin_nfe_line_id = fields.Many2one(
        comodel_name="l10n_br_fiscal.document.line",
        string="Linha na nota de Origem",
    )
    simple_name = fields.Char(string="Nome simples", compute="_compute_simple_name")

    @api.model
    def _get_default_origin_picking(self):
        picking_id = self.env.context.get("default_origin_picking_id")
        return self.env["stock.picking"].browse(picking_id)

    @api.model
    def _get_default_origin_order(self, model):
        picking = self._get_default_origin_picking()
        if not picking.origin:
            return False
        return self.env[model].search([("name", "=", picking.origin)], limit=1).id

    @api.depends("name")
    def _compute_simple_name(self):
        for record in self:
            record.simple_name = (record.name or "").split(ORIGIN_SEPARATOR)[0]

    @api.onchange("name")
    def _onchange_name_add_origin(self):
        for record in self:
            if record.name and ORIGIN_SEPARATOR not in record.name and record.origin:
                record.name = f"{record.name}{ORIGIN_SEPARATOR}{record.origin}]"

    @api.model_create_multi
    def create(self, vals_list):
        picking = self._get_default_origin_picking()
        for vals in vals_list:
            origin = vals.get("origin") or picking.origin
            if origin and vals.get("name"):
                simple = vals["name"].split(ORIGIN_SEPARATOR)[0]
                vals["name"] = f"{simple}{ORIGIN_SEPARATOR}{origin}]"
        lots = super().create(vals_list)
        if picking:
            for lot in lots:
                lot._set_origin_nfe_from_picking(picking)
        return lots

    def _set_origin_nfe_from_picking(self, picking):
        """O lote criado no recebimento herda a nota e a linha da nota do
        movimento do mesmo produto."""
        self.ensure_one()
        move = (
            self.env["stock.move.line"]
            .browse(self.env.context.get("default_origin_stock_move_line_id"))
            .move_id
        )
        if not move.origin_nfe_id:
            move = fields.first(
                picking.move_ids.filtered(
                    lambda m: m.product_id == self.product_id and m.origin_nfe_id
                )
            )
        if not move:
            return
        self.write(
            {
                "origin_nfe_id": move.origin_nfe_id.id,
                "origin_nfe_line_id": move.origin_nfe_line_id.id,
                "numero_nota": move.origin_nfe_id.document_number,
            }
        )
