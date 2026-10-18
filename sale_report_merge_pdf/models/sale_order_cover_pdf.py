from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderCoverPdf(models.Model):
    _name = "sale.order.cover.pdf"
    _description = "PDF de Capa para Pedidos de Venda"
    _rec_name = "display_name"

    display_name = fields.Char(
        string="Nome", default="Capa Padrão dos Pedidos", readonly=True
    )
    cover_pdf = fields.Binary(
        string="PDF da Capa",
        help="PDF que será usado como capa em todos os pedidos de venda.",
    )
    cover_pdf_filename = fields.Char(string="Nome do Arquivo")
    active = fields.Boolean(string="Ativo", default=True)

    @api.constrains("active")
    def _check_single_record(self):
        """Garante que só existe um registro ativo por vez"""
        if self.active:
            other_active = self.search([("id", "!=", self.id), ("active", "=", True)])
            if other_active:
                raise ValidationError(
                    _(
                        "Só pode existir um registro ativo de capa PDF por vez. "
                        "Desative o registro atual antes de ativar outro."
                    )
                )

    @api.model
    def create(self, vals):
        if vals.get("active", True):
            existing_active = self.search([("active", "=", True)])
            if existing_active:
                raise ValidationError(
                    _(
                        "Já existe um registro ativo de capa PDF. "
                        "Desative-o antes de criar um novo."
                    )
                )
        return super().create(vals)

    @api.model
    def get_active_cover(self):
        """Retorna a capa ativa ou None"""
        cover = self.search([("active", "=", True)], limit=1)
        return cover if cover and cover.cover_pdf else None
