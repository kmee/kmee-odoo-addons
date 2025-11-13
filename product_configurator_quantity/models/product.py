from odoo import api, fields, models
from odoo.tools.sql import drop_index, index_exists
from odoo.exceptions import ValidationError
from odoo import _


class ProductConfigAttributeValueQty(models.Model):
    _name = "product.config.attribute.value.qty"
    _description = "Configurator Value Quantity"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    config_line_id = fields.Many2one(
        "product.config.line",
        string="Configuration Line",
        required=True,
        ondelete="cascade",
        index=True,
    )
    value_id = fields.Many2one(
        "product.attribute.value",
        string="Attribute Value",
        required=True,
    )
    attribute_id = fields.Many2one(
        "product.attribute",
        string="Attribute",
        compute="_compute_attribute",
        store=True,
    )

    qty = fields.Float(string="Quantity", default=1.0)
    qty_min = fields.Float(string="Min Quantity", default=0.0)
    qty_max = fields.Float(string="Max Quantity", default=0.0)

    @api.depends('value_id')
    def _compute_attribute(self):
        for rec in self:
            rec.attribute_id = rec.value_id.attribute_id if rec.value_id else False

    @api.constrains("qty", "qty_min", "qty_max")
    def _check_qty_range(self):
        for rec in self:
            if rec.qty_min and rec.qty_max and rec.qty_min > rec.qty_max:
                raise ValidationError(_("Min quantity cannot be greater than max quantity."))
            if rec.qty_min and rec.qty < rec.qty_min:
                raise ValidationError(_("Quantity is below the minimum allowed."))
            if rec.qty_max and rec.qty > rec.qty_max:
                raise ValidationError(_("Quantity is above the maximum allowed."))

class ProductConfigLine(models.Model):
    _inherit = "product.config.line"

    value_qty_ids = fields.One2many(
        "product.config.attribute.value.qty",
        "config_line_id",
        string="Values with Quantities",
    )

    def get_selected_values_with_qty(self):
        """Retorna [(value_id, qty)] para integrar com preço/BoM."""
        self.ensure_one()
        return [(l.value_id, l.qty) for l in self.value_qty_ids if l.value_id and l.qty]

    @api.onchange('value_ids')
    def _onchange_value_ids_seed_qty(self):
        """
        Sempre que os valores forem (re)selecionados no wizard,
        semeia/atualiza `value_qty_ids` a partir dos defaults do template (PTAV).
        """
        for line in self:
            if not line.value_ids or not line.config_id or not line.config_id.product_tmpl_id:
                line.value_qty_ids = [(5, 0, 0)]
                continue

            tmpl = line.config_id.product_tmpl_id  # produto do configurador
            # mapa value_id -> (qty, min, max) vindos do template
            defaults = {}
            # acha PTAVs do template em questão
            ptavs = self.env['product.template.attribute.value'].search([
                ('product_tmpl_id', '=', tmpl.id),
                ('product_attribute_value_id', 'in', line.value_ids.ids),
            ])
            if ptavs:
                qty_recs = self.env['product.template.attribute.value.qty'].search([
                    ('template_attri_value_id', 'in', ptavs.ids)
                ])
                for q in qty_recs:
                    defaults[q.product_attribute_value_id.id] = (q.qty, q.qty_min, q.qty_max)

            # Monta linhas novas preservando qty já editadas quando possível
            existing_map = {rec.value_id.id: rec for rec in line.value_qty_ids}
            new_lines = []
            for val in line.value_ids:
                if val.id in existing_map:
                    # mantém o que o usuário já editou
                    rec = existing_map[val.id]
                    new_lines.append((1, rec.id, {
                        # mantém qty atual; atualiza limites caso mudem no template
                        'qty_min': defaults.get(val.id, (rec.qty_min, 0.0, 0.0))[1],
                        'qty_max': defaults.get(val.id, (rec.qty_max, 0.0, 0.0))[2],
                    }))
                else:
                    q, qmin, qmax = defaults.get(val.id, (1.0, 0.0, 0.0))
                    new_lines.append((0, 0, {
                        'value_id': val.id,
                        'qty': q,
                        'qty_min': qmin,
                        'qty_max': qmax,
                    }))

            # remove linhas de valores que não estão mais selecionados
            to_remove = [rec.id for vid, rec in existing_map.items() if vid not in line.value_ids.ids]
            ops = []
            if to_remove:
                for rid in to_remove:
                    ops.append((2, rid, 0))
            ops.extend(new_lines)
            line.value_qty_ids = ops


class ProductProductAttributeValueQty(models.Model):
    _name = "product.product.attribute.value.qty"
    _description = "Product Variant Attribute Value Quantity"
    _order = "id"

    product_id = fields.Many2one(
        "product.product",
        string="Product Variant",
        required=True,
        ondelete="cascade",
        index=True,
    )
    attr_value_id = fields.Many2one(
        "product.attribute.value",
        string="Attribute Value",
        required=True,
    )
    qty = fields.Float(string="Quantity", default=1.0)
    attribute_value_qty_id = fields.Many2one(
        "product.template.attribute.value.qty",
        string="Template Value Qty",
        ondelete="set null",
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    product_attribute_value_qty_ids = fields.One2many(
        "product.product.attribute.value.qty",
        "product_id",
        string="Attribute Value Quantities",
    )
