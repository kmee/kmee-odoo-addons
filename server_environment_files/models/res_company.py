from odoo import api

from odoo.addons.spec_driven_model.models import spec_models


class ResCompany(spec_models.SpecModel):
    _name = "res.company"
    _inherit = ["res.company", "server.env.mixin"]

    @property
    def _server_env_fields(self):
        base_fields = super()._server_env_fields
        env_fields = {}

        if hasattr(self, "nfe_environment"):
            env_fields["nfe_environment"] = {}
        if hasattr(self, "nfse_environment"):
            env_fields["nfse_environment"] = {}

        env_fields.update(base_fields)
        return env_fields

    @api.model
    def _server_env_global_section_name(self):
        """Name of the global section in the configuration files

        Can be customized in your model
        """
        return "res_company_environment"
