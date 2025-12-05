from odoo import _, fields, models
from odoo.exceptions import UserError


class NewMoneteryTrackWizard(models.TransientModel):
    _name = "new.monetery.track.wizard"
    _description = "New Monetery Track Wizard"

    model_id = fields.Many2one("ir.model", string="Model")
    res_id = fields.Integer(string="Record ID")
    field_ids = fields.Many2many(
        "ir.model.fields",
        string="Fields",
        domain="[('model_id', '=', model_id), ('ttype', '=', 'monetary')]",
    )
    index_id = fields.Many2one("monetary.update.index", string="Index")
    last_update_date = fields.Date(string="Last Update Date")
    end_date = fields.Date(string="End Date", default=fields.Date.today())

    def create_monetery_track(self):
        for field in self.field_ids:
            exists = self.env["monetary.update.field.state"].search(
                [
                    ("model_id", "=", self.model_id.id),
                    ("res_id", "=", self.res_id),
                    ("field_id", "=", field.id),
                ]
            )
            if exists:
                raise UserError(
                    _(
                        "Monetary track already exists for field '%s'!. If you want to update the track, please delete the existing track first."
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
                start_date=self.last_update_date,
                end_date=self.end_date,
            )
            record.write({field.name: updated_amount})

            self.env["monetary.update.field.state"].create(
                {
                    "model_id": self.model_id.id,
                    "res_id": self.res_id,
                    "field_id": field.id,
                    "index_id": self.index_id.id,
                    "last_update_date": self.end_date,
                }
            )
