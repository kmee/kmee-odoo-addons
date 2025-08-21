from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class ProductTemplateAttributeValueQty(models.Model):
    _name = "product.template.attribute.value.qty"
    _description = "Template Attribute Value Quantity Defaults"
    _order = "sequence, qty"
    _sql_constraints = [
        ("ptav_qty_unique",
         "unique(template_attri_value_id, qty)",
         "Duplicated quantity for this attribute value."),
    ]

    sequence = fields.Integer(default=10)
    product_tmpl_id = fields.Many2one("product.template", required=True, index=True)
    product_attribute_id = fields.Many2one("product.attribute", required=True)
    product_attribute_value_id = fields.Many2one("product.attribute.value", required=True)
    # Recomendado deixar required=True; o create() abaixo sempre preenche
    template_attri_value_id = fields.Many2one(
        "product.template.attribute.value",
        required=True,
        ondelete="cascade",
    )

    qty = fields.Float(default=1.0)
    qty_min = fields.Float(default=0.0)
    qty_max = fields.Float(default=0.0)

    @api.model_create_multi
    def create(self, vals_list):
        PAV = self.env["product.attribute.value"]
        PTAV = self.env["product.template.attribute.value"]
        for vals in vals_list:
            ptav_id = vals.get("template_attri_value_id")
            pav_id = vals.get("product_attribute_value_id")
            tmpl_id = vals.get("product_tmpl_id")
            attr_id = vals.get("product_attribute_id")

            # Se veio o PTAV, derive os demais
            if ptav_id:
                ptav = PTAV.browse(ptav_id).exists()
                if ptav:
                    vals.setdefault("product_tmpl_id", ptav.product_tmpl_id.id)
                    vals.setdefault("product_attribute_value_id", ptav.product_attribute_value_id.id)
                    vals.setdefault("product_attribute_id", ptav.attribute_id.id)

            # Se veio só PAV, derive o atributo
            if pav_id and not attr_id:
                vals["product_attribute_id"] = PAV.browse(pav_id).attribute_id.id

            # Se veio tmpl + pav mas não o PTAV, localize
            if tmpl_id and pav_id and not vals.get("template_attri_value_id"):
                ptav = PTAV.search([
                    ("product_tmpl_id", "=", tmpl_id),
                    ("product_attribute_value_id", "=", pav_id),
                ], limit=1)
                if ptav:
                    vals["template_attri_value_id"] = ptav.id

            # Garanta que sempre teremos o PTAV — evita linhas “soltas”
            if not vals.get("template_attri_value_id"):
                raise ValidationError(
                    _("No Template Attribute Value found for this Template + Value. "
                      "Add the attribute value to the product template first.")
                )

        # NUNCA escrever/alterar attribute_line aqui (evita recursão)
        return super().create(vals_list)

    # Limita opções ao template selecionado
    @api.onchange("product_tmpl_id")
    def _onchange_product_tmpl_id(self):
        if not self.product_tmpl_id:
            return {}
        attr_ids = self.product_tmpl_id.attribute_line_ids.mapped("attribute_id").ids
        pav_ids = self.product_tmpl_id.attribute_line_ids.mapped("value_ids").ids
        return {
            "domain": {
                "product_attribute_id": [("id", "in", attr_ids)],
                "product_attribute_value_id": [("id", "in", pav_ids)],
            }
        }

    # Ao escolher o valor, preenche o atributo e tenta apontar o PTAV
    @api.onchange("product_attribute_value_id")
    def _onchange_product_attribute_value_id(self):
        if self.product_attribute_value_id:
            self.product_attribute_id = self.product_attribute_value_id.attribute_id
            if self.product_tmpl_id:
                ptav = self.env["product.template.attribute.value"].search([
                    ("product_tmpl_id", "=", self.product_tmpl_id.id),
                    ("product_attribute_value_id", "=", self.product_attribute_value_id.id),
                ], limit=1)
                self.template_attri_value_id = ptav

    # Mantém coerência dos campos e das faixas
    @api.constrains(
        "product_tmpl_id",
        "product_attribute_id",
        "product_attribute_value_id",
        "template_attri_value_id",
        "qty_min", "qty_max", "qty",
    )
    def _check_consistency(self):
        for rec in self:
            # A) Atributo do valor deve bater com o atributo
            if rec.product_attribute_value_id.attribute_id != rec.product_attribute_id:
                raise ValidationError(_("Selected value does not belong to the selected attribute."))

            # B) O valor deve existir nas linhas de atributo do template
            line = rec.product_tmpl_id.attribute_line_ids.filtered(
                lambda l: l.attribute_id == rec.product_attribute_id
            )
            if not line or rec.product_attribute_value_id not in line.value_ids:
                raise ValidationError(_("This value is not available on the product template."))

            # C) PTAV deve casar com template e valor
            if (rec.template_attri_value_id.product_tmpl_id != rec.product_tmpl_id or
                rec.template_attri_value_id.product_attribute_value_id != rec.product_attribute_value_id):
                raise ValidationError(_("Template Attribute Value mismatch."))

            # D) Faixas de quantidade coerentes
            if rec.qty_min < 0 or rec.qty_max < 0 or rec.qty < 0:
                raise ValidationError(_("Quantities must be non-negative."))
            if rec.qty_max and rec.qty_min and rec.qty_min > rec.qty_max:
                raise ValidationError(_("Min quantity cannot be greater than Max quantity."))
            if rec.qty_max and rec.qty > rec.qty_max:
                raise ValidationError(_("Default quantity must be <= Max quantity."))
            if rec.qty < rec.qty_min:
                raise ValidationError(_("Default quantity must be >= Min quantity."))
            