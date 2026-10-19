# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest import mock

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMinhaReceita(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "l10n_br_cnpj_search.cnpj_provider", "minhareceita"
        )
        cls.webservice = cls.env["l10n_br_cnpj_search.webservice.abstract"]

    def test_provider_dispatch(self):
        self.assertEqual(self.webservice.get_provider(), "minhareceita")
        url = self.webservice.get_api_url("12345678000195")
        self.assertTrue(url.endswith("12345678000195"))
        self.assertEqual(self.webservice.get_headers(), {"Accept": "application/json"})

    def test_validate(self):
        response = mock.Mock(status_code=200)
        response.json.return_value = {"razao_social": "ACME"}
        self.assertEqual(self.webservice.validate(response), {"razao_social": "ACME"})
        response.json.return_value = {"status": "ERROR", "message": "Not found"}
        with self.assertRaises(ValidationError):
            self.webservice.validate(response)
        bad = mock.Mock(status_code=500, reason="Server error")
        with self.assertRaises(ValidationError):
            self.webservice.validate(bad)

    def test_import_data(self):
        data = {
            "razao_social": "ACME LTDA",
            "nome_fantasia": "",
            "email": "CONTATO@ACME.COM",
            "logradouro": "RUA A",
            "numero": "10",
            "cep": "01001000",
            "ddd_telefone_1": "1133334444",
            "uf": "SP",
            "cnaes_secundarios": [],
        }
        values = self.webservice.import_data(data)
        self.assertEqual(values["legal_name"], "Acme Ltda")
        self.assertEqual(values["name"], "Acme Ltda")
        self.assertEqual(values["email"], "contato@acme.com")
        self.assertEqual(values["street_name"], "Rua A")
        self.assertEqual(values["phone"], "1133334444")
        self.assertFalse(values["cnae_main_id"])
        self.assertFalse(values["legal_nature_id"])
