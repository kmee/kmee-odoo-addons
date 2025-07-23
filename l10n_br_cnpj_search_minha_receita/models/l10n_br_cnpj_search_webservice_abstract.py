# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError

MINHARECEITA_URL = "https://search-br-data.kmee.dev.br/"  # TODO tornar url configurável


class L10nBrCnpjSearchWebserviceAbstract(models.AbstractModel):

    _inherit = "l10n_br_cnpj_search.webservice.abstract"

    def minhareceita_get_api_url(self, cnpj):
        return MINHARECEITA_URL + cnpj

    def minhareceita_get_api_headers(self):
        return {"Accept": "application/json"}

    def minhareceita_validate(self, response):
        self._validate(response)
        data = response.json()
        if data.get("status") == "ERROR":
            raise ValidationError(_(data.get("message")))

        return data

    def _minhareceita_import_data(self, data):
        legal_name = self.get_data(data, "razao_social", title=True)
        fantasy_name = self.get_data(data, "nome_fantasia", title=True)
        state_id, city_id = self._get_state_city(data)
        res = {
            "legal_name": legal_name,
            "name": fantasy_name if fantasy_name else legal_name,
            "email": self.get_data(data, "email", lower=True),
            "street_name": self.get_data(data, "logradouro", title=True),
            "street2": self.get_data(data, "complemento", title=True),
            "district": self.get_data(data, "bairro", title=True),
            "street_number": self.get_data(data, "numero"),
            "zip": self.get_data(data, "cep"),
            "legal_nature": self.get_data(data, "natureza_juridica"),
            "phone": self.get_data(data, "ddd_telefone_1"),
            "mobile": self.get_data(data, "ddd_telefone_2"),
            "state_id": state_id,
            "city_id": city_id,
            "equity_capital": self.get_data(data, "capital_social"),
            "cnae_main_id": self._minhareceita_get_cnae(data),
            "cnae_secondary_ids": self._minhareceita_get_secondary_cnae(data),
        }
        return res

    @api.model
    def _minhareceita_get_cnae(self, data):
        cnae_code = data.get("cnae_fiscal")
        if cnae_code:
            return self._get_cnae(str(cnae_code or ""))
        return False

    @api.model
    def _minhareceita_get_secondary_cnae(self, data):
        cnae_secondary = []
        for atividade in data.get("cnaes_secundarios", []):
            code = self.get_data(atividade, "codigo")
            if self._get_cnae(str(code or "")):
                cnae_secondary.append(self._get_cnae(str(code or "")))
        return cnae_secondary
