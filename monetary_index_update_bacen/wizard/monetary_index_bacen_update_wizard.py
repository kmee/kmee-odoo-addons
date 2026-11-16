from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MonetaryIndexBacenUpdateWizard(models.TransientModel):
    _name = "monetary.index.bacen.update.wizard"
    _description = "Banco Central (SGS) Index Update Wizard"

    def _default_date_from(self):
        today = fields.Date.today()
        return (today - relativedelta(months=1)).replace(day=1)

    @api.model
    def _default_index_id(self):
        if self.env.context.get("active_model") == "monetary.index":
            return self.env.context.get("active_id")
        return False

    index_id = fields.Many2one(
        comodel_name="monetary.index",
        string="Índice",
        required=True,
        default=_default_index_id,
        domain=[("bcb_sgs_code", "!=", False)],
    )
    date_from = fields.Date(
        string="Data Inicial", required=True, default=_default_date_from
    )
    date_to = fields.Date(string="Data Final", required=True, default=fields.Date.today)
    force = fields.Boolean(string="Forçar reimportação")

    def action_update(self):
        self.ensure_one()
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(
                _("A data inicial deve ser anterior ou igual à data final.")
            )

        result = self.env["monetary.index.provider"].update_rates(
            self.index_id,
            date_from=self.date_from,
            date_to=self.date_to,
            force=self.force,
        )
        result["name"] = self.index_id.name
        message = (
            _(
                "%(name)s atualizado. Criados: %(created)d, "
                "Atualizados: %(updated)d, Ignorados: %(skipped)d."
            )
            % result
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Atualização pelo Banco Central"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }
