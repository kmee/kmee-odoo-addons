from odoo import api, fields, models

class ProductConfigSession(models.Model):
    _inherit = "product.config.session"

    # Linhas de quantidade por valor na sessão
    session_value_quantity_ids = fields.One2many(
        "product.config.session.value.qty",
        "session_id",
        string="Values with Quantities",
    )


class ProductConfigSessionValueQty(models.Model):
    _name = "product.config.session.value.qty"
    _description = "Configurator Session - Value Quantities"
    _order = "id"

    session_id = fields.Many2one(
        "product.config.session",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_attribute_id = fields.Many2one("product.attribute", required=True)
    attr_value_id = fields.Many2one("product.attribute.value", required=True)

    # Se quiser atrelar ao bind materializado do template:
    template_value_qty_id = fields.Many2one(
        "product.template.attribute.value.qty",
        string="Template Value Qty",
        ondelete="set null",
    )

    qty = fields.Float(string="Quantity", default=1.0)


class ProductConfigurator(models.TransientModel):
    _inherit = "product.configurator"

    # espelho no wizard, editável, apontando para a sessão
    session_value_quantity_ids = fields.One2many(
        related="config_session_id.session_value_quantity_ids",
        string="Values with Quantities",
        readonly=False,
    )
