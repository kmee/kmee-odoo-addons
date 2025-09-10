# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"
    netsuite_account_id = fields.Char(
        string="Account ID",
        config_parameter="netsuite_synchronizer.netsuite_account_id",
    )
    netsuite_email = fields.Char(
        string="NLAuth Email", config_parameter="netsuite_synchronizer.netsuite_email"
    )
    netsuite_password = fields.Char(
        string="NLAuth Senha",
        config_parameter="netsuite_synchronizer.netsuite_password",
    )
    netsuite_role_id = fields.Char(
        string="NLAuth Role ID",
        config_parameter="netsuite_synchronizer.netsuite_role_id",
    )
    netsuite_restlet_url = fields.Char(
        string="RESTlet URL",
        config_parameter="netsuite_synchronizer.netsuite_restlet_url",
    )
    netsuite_fin_field = fields.Char(
        string="Nome interno Situação",
        config_parameter="netsuite_synchronizer.netsuite_fin_field",
    )
    netsuite_saved_search_id = fields.Char(
        string="Saved Search ID",
        config_parameter="netsuite_synchronizer.netsuite_saved_search_id",
    )
