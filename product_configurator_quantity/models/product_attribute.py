from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

MAX_MATERIALIZED_QTYS = 500

class ProductAttributeLine(models.Model):
    _inherit = "product.template.attribute.line"

    is_qty_required = fields.Boolean(string="Qty Required", copy=False)

    def _materialize_qty_for_ptav(self, ptav):
        """Cria registros discretos (default..maximum) para um PTAV."""
        if ptav.default_qty is None or ptav.maximum_qty is None:
            return
        span = ptav.maximum_qty - ptav.default_qty + 1
        if span <= 0:
            return
        if span > MAX_MATERIALIZED_QTYS:
            raise ValidationError(_("Quantity range is too large to materialize (%s).") % span)

        vals_list = []
        for i in range(ptav.default_qty, ptav.maximum_qty + 1):
            vals_list.append({
                "product_tmpl_id": ptav.product_tmpl_id.id,
                "product_attribute_id": ptav.attribute_id.id,
                "product_attribute_value_id": ptav.product_attribute_value_id.id,
                "qty": i,
                "template_attri_value_id": ptav.id,
            })
        self.env["product.template.attribute.value.qty"].create(vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Materializa por linha criada
        for line in records:
            if not line.is_qty_required or not line.value_ids:
                continue
            ptavs = self.env["product.template.attribute.value"].search([
                ("product_tmpl_id", "=", line.product_tmpl_id.id),
                ("attribute_line_id", "=", line.id),
                ("attribute_id", "=", line.attribute_id.id),
                ("product_attribute_value_id", "in", line.value_ids.ids),
            ])
            for ptav in ptavs:
                line._materialize_qty_for_ptav(ptav)
        return records

    def _get_attribute_value_line_domain(self):
        self.ensure_one()
        return [
            ("product_tmpl_id", "=", self.product_tmpl_id.id),
            ("attribute_line_id", "=", self.id),
            ("attribute_id", "=", self.attribute_id.id),
        ]

    def write(self, values):
        res = super().write(values)

        for line in self:
            # habilitou a flag agora?
            if values.get("is_qty_required") and line.value_ids:
                ptavs = self.env["product.template.attribute.value"].search(
                    line._get_attribute_value_line_domain() + [
                        ("product_attribute_value_id", "in", line.value_ids.ids),
                    ]
                )
                for ptav in ptavs:
                    # recria a faixa (apaga antes p/ consistência)
                    ptav.attribute_value_qty_ids.unlink()
                    line._materialize_qty_for_ptav(ptav)

            # desabilitou a flag agora?
            if "is_qty_required" in values and not values["is_qty_required"]:
                ptavs = self.env["product.template.attribute.value"].search(
                    line._get_attribute_value_line_domain()
                )
                ptavs_with_qty = ptavs.filtered(lambda p: p.attribute_value_qty_ids)

                # Encontra todas as variantes que usam valores deste atributo
                qty_variants = line.product_tmpl_id.product_variant_ids.filtered(
                    lambda v: bool(v.product_template_attribute_value_ids & ptavs_with_qty)
                )

                # Remove quantidades das variantes de forma recursiva
                if qty_variants:
                    # Pega os valores de atributo relacionados a este atributo
                    attr_value_ids = ptavs_with_qty.mapped("product_attribute_value_id").ids
                    
                    # Remove os registros de quantidade das variantes para este atributo
                    for variant in qty_variants:
                        variant.product_attribute_value_qty_ids.filtered(
                            lambda q: q.attr_value_id.id in attr_value_ids
                        ).unlink()

                # Apaga as faixas no template
                ptavs.mapped("attribute_value_qty_ids").unlink()

        return res

    @api.onchange("is_qty_required", "multi", "custom")
    def onchange_is_qty_required(self):
        if self.is_qty_required and (self.multi or self.custom):
            self.is_qty_required = False


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    is_qty_required = fields.Boolean(related="attribute_line_id.is_qty_required", store=True, copy=False)
    default_qty = fields.Integer("Minimum Quantity", default=1)
    maximum_qty = fields.Integer("Maximum Quantity", default=2)

    attribute_value_qty_ids = fields.One2many(
        "product.template.attribute.value.qty", "template_attri_value_id", string="Value Quantity"
    )

    @api.constrains("default_qty", "maximum_qty")
    def _check_default_qty_maximum_qty(self):
        for rec in self:
            if rec.default_qty > rec.maximum_qty:
                raise ValidationError(_("Maximum Qty can't be smaller than Default Qty"))

    def write(self, values):
        res = super().write(values)
        # Se alterou default/max e a linha requer qty, rematerializa
        if any(k in values for k in ("default_qty", "maximum_qty")):
            for ptav in self:
                if not ptav.is_qty_required:
                    continue
                ptav.attribute_value_qty_ids.unlink()
                ptav.attribute_line_id._materialize_qty_for_ptav(ptav)
        return res
