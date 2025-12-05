from odoo import _, fields, models
from odoo.exceptions import UserError


class UpdateFieldByIndexWizard(models.TransientModel):
    _name = "update.field.by.index.wizard"
    _description = "Update Field by Index Wizard"

    model_id = fields.Many2one("ir.model", string="Model")
    res_id = fields.Integer(string="Record ID")
    field_ids = fields.Many2many(
        "ir.model.fields",
        string="Fields",
        domain="[('model_id', '=', model_id), ('ttype', '=', 'monetary')]",
    )
    index_id = fields.Many2one("monetary.update.index", string="Index")
    end_date = fields.Date(string="End Date", default=fields.Date.today())

    def update_fields_by_index(self):
        for field in self.field_ids:
            field_state = self.env["monetary.update.field.state"].search(
                [
                    ("model_id", "=", self.model_id.id),
                    ("res_id", "=", self.res_id),
                    ("field_id", "=", field.id),
                ]
            )
            if not field_state:
                raise UserError(
                    _(
                        "Monetary track for field '%s' not found!. Please create a new track first."
                        % field.name
                    )
                )

            record = self.env[self.model_id.model].browse(self.res_id)
            if not record:
                raise UserError(_("Record '%s' not found!" % self.res_id))

            amount = eval("record." + field.name)
            if not amount:
                raise UserError(_("Amount for field '%s' is not set!" % field.name))

            updated_amount = self.env["monetary.update.service"].compute_updated_amount(
                index_code=self.index_id.code,
                amount=amount,
                start_date=field_state.last_update_date,
                end_date=self.end_date,
            )
            record.write({field.name: updated_amount})
            field_state.last_update_date = self.end_date
