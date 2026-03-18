from odoo import _, fields, models
from odoo.exceptions import RedirectWarning


class PosConfig(models.Model):
    _inherit = "pos.config"

    is_van_config = fields.Boolean()
    van_load_picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Load Picking Type",
    )
    van_unload_picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Unload Picking Type",
    )
    van_driver_account_id = fields.Many2one(
        "account.account",
        string="Driver Account",
    )
    van_transit_account_id = fields.Many2one(
        "account.account",
        string="Van Transit Account",
    )
    van_cash_account_id = fields.Many2one(
        "account.account",
        string="Cash Account",
    )
    van_journal_id = fields.Many2one(
        "account.journal",
        string="Van Journal",
    )

    def _check_before_creating_new_session(self):
        result = super()._check_before_creating_new_session()
        if self.is_van_config:
            session = self.env["van.session"].search(
                [
                    ("pos_config_id", "=", self.id),
                    ("state", "=", "loaded"),
                ],
                limit=1,
            )
            if not session:
                action = self.env.ref("van_sales.action_van_session")
                raise RedirectWarning(
                    _("Valide o carregamento antes de abrir o POS."),
                    action.id,
                    _("Ir para Sessões Van"),
                )
        return result

    def open_ui(self):
        res = super().open_ui()
        if self.is_van_config and self.current_session_id:
            van_session = self.env["van.session"].search(
                [
                    ("pos_config_id", "=", self.id),
                    ("state", "=", "loaded"),
                ],
                limit=1,
            )
            if van_session:
                self.current_session_id.van_session_id = van_session
                van_session.pos_session_id = self.current_session_id
                van_session.state = "in_route"
        return res
