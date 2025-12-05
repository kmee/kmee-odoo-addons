from odoo import api, fields, models


class MonetaryUpdateFieldState(models.Model):
    _name = "monetary.update.field.state"
    _description = "Estado de atualização monetária por registro e campo"
    _rec_name = "display_name"

    model_id = fields.Many2one(
        comodel_name="ir.model",
        ondelete="cascade",
        compute="_compute_model_id",
        store=True,
    )
    res_id = fields.Integer(string="ID do Registro", required=True)

    field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        required=True,
        ondelete="cascade",
        domain=[("ttype", "=", "monetary")],
    )

    last_update_date = fields.Date(required=True)
    index_id = fields.Many2one(
        comodel_name="monetary.update.index", required=True, ondelete="cascade"
    )

    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("model_id", "res_id", "field_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.model_id.model},{rec.res_id} - {rec.field_id.name}"
            )

    @api.depends("field_id")
    def _compute_model_id(self):
        for rec in self:
            rec.model_id = rec.field_id.model_id
