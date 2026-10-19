from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MonetaryUpdateByIndexWizard(models.TransientModel):
    _name = "monetary.update.by.index.wizard"
    _description = "Monetary Update by Index Wizard"

    model_id = fields.Many2one("ir.model", required=True)
    res_id = fields.Integer(required=True)
    index_id = fields.Many2one("monetary.index", required=True)
    start_date = fields.Date()
    end_date = fields.Date(default=fields.Date.today(), required=True)
    result_preview = fields.Text(compute="_compute_result_preview")

    def _compute_updated_amounts(self):
        record = self.env[self.model_id.model].browse(self.res_id)
        if not record:
            raise UserError(_("Record '%s' not found!") % self.res_id)

        fields_to_update = {}
        for field in self.env.context.get("field_names"):
            amount = getattr(record, field)
            if not amount:
                raise UserError(_("Amount for field '%s' is not set!") % field.name)

            updated_amount = self.env["monetary.update.service"].compute_updated_amount(
                index_code=self.index_id.code,
                amount=amount,
                start_date=self.start_date,
                end_date=self.end_date,
            )
            fields_to_update[field] = {
                "original": amount,
                "updated": updated_amount,
                "percentage": ((updated_amount - amount) / amount * 100)
                if amount
                else 0,
            }
        return fields_to_update.items()

    @api.depends("model_id", "res_id", "index_id", "start_date", "end_date")
    def _compute_result_preview(self):
        for rec in self:
            if rec.index_id and rec.start_date and rec.end_date:
                preview_lines = []
                model = rec.env[rec.model_id.model]
                fields_info = model.fields_get(rec.env.context.get("field_names", []))
                for field, values in rec._compute_updated_amounts():
                    field_label = fields_info.get(field, {}).get("string", field)
                    updated = values["updated"]
                    percentage = values["percentage"]
                    sign = "+" if percentage > 0 else ""
                    preview_lines.append(
                        f"{field_label}: {updated:,.2f} ({sign}{percentage:.2f}%)"
                    )
                rec.result_preview = "\n".join(preview_lines)
            else:
                rec.result_preview = ""

    def update_fields_by_index(self):
        record = self.env[self.model_id.model].browse(self.res_id)
        if not record:
            raise UserError(_("Record '%s' not found!") % self.res_id)

        fields_to_update = {
            field: values["updated"]
            for field, values in self._compute_updated_amounts()
        }
        fields_to_update["last_monetary_update_date"] = self.end_date
        record.write(fields_to_update)
