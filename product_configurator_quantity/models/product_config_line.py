from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

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
        self.ensure_one()
        return [(l.value_id, l.qty) for l in self.value_qty_ids if l.value_id and l.qty]

    @api.onchange('value_ids')
    def _onchange_value_ids_seed_qty(self):
        for line in self:
            # Descobre o template de forma robusta
            tmpl = False
            if hasattr(line, "wizard_id") and line.wizard_id:
                tmpl = line.wizard_id.product_tmpl_id
            elif hasattr(line, "configurator_id") and line.configurator_id:
                tmpl = line.configurator_id.product_tmpl_id
            elif hasattr(line, "product_tmpl_id") and line.product_tmpl_id:
                tmpl = line.product_tmpl_id

            # Se não tem valores ou não conseguiu achar o template, limpa e segue
            if not line.value_ids or not tmpl:
                line.value_qty_ids = [(5, 0, 0)]
                continue

            # PTAVs do template para os valores selecionados
            ptavs = self.env['product.template.attribute.value'].search([
                ('product_tmpl_id', '=', tmpl.id),
                ('product_attribute_value_id', 'in', line.value_ids.ids),
            ])

            # Pega defaults (ex.: menor qty) e carrega também min/max do bind do template
            defaults = {}
            if ptavs:
                qty_defaults = self.env['product.template.attribute.value.qty'].search([
                    ('template_attri_value_id', 'in', ptavs.ids)
                ])
                for q in qty_defaults.sorted(key=lambda r: (r.product_attribute_value_id.id, r.qty)):
                    if q.product_attribute_value_id.id not in defaults:
                        defaults[q.product_attribute_value_id.id] = {
                            'qty': q.qty,
                            'qty_min': q.qty_min or 0.0,
                            'qty_max': q.qty_max or 0.0,
                        }

            existing = {rec.value_id.id: rec for rec in line.value_qty_ids}
            ops = []

            # remove os que saíram
            to_remove = [rec.id for vid, rec in existing.items() if vid not in line.value_ids.ids]
            for rid in to_remove:
                ops.append((2, rid, 0))

            # cria os que entraram
            for val in line.value_ids:
                if val.id in existing:
                    continue
                d = defaults.get(val.id, {'qty': 1.0, 'qty_min': 0.0, 'qty_max': 0.0})
                ops.append((0, 0, {
                    'value_id': val.id,
                    'qty': d.get('qty', 1.0),
                    'qty_min': d.get('qty_min', 0.0),
                    'qty_max': d.get('qty_max', 0.0),
                }))

            if ops:
                line.value_qty_ids = ops
