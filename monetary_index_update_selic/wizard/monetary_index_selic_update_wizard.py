from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class MonetaryIndexSelicUpdateWizard(models.TransientModel):
    _name = "monetary.index.selic.update.wizard"
    _description = "SELIC Update Wizard"

    def _default_date_from(self):
        today = fields.Date.today()
        return (today - relativedelta(months=1)).replace(day=1)

    date_from = fields.Date(
        string="Data Inicial", required=True, default=_default_date_from
    )
    date_to = fields.Date(string="Data Final", required=True, default=fields.Date.today)
    force = fields.Boolean(string="Forcar Reimportacao")

    def action_update(self):
        self.ensure_one()
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(
                _("A data inicial deve ser anterior ou igual à data final.")
            )

        result = self.env["monetary.index.provider"].update_selic_rates(
            date_from=self.date_from,
            date_to=self.date_to,
            force=self.force,
        )

        message = (
            _(
                "SELIC atualizada com sucesso. Criados: %(created)d, "
                "Atualizados: %(updated)d, Ignorados: %(skipped)d."
            )
            % result
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Atualizacao SELIC"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }
