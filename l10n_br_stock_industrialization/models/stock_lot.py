from odoo import fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    lot_for_industrialization = fields.Selection(
        selection=[("yes", "Sim"), ("no", "Não")],
        string="Lote para industrialização",
        help="Indica se o lote é de material do cliente recebido para "
        "industrialização.",
    )

    def _get_origin_unit_price(self, product, uom):
        """Preço do produto na unidade `uom`, pelo valor da nota de origem do
        lote; sem nota, o custo do produto."""
        self.ensure_one()
        line = self.origin_nfe_line_id
        if not line:
            return product.standard_price
        return line.uom_id._compute_price(line.price_unit, uom)
