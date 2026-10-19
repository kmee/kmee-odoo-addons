# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

WIZARD_REQUESTS_GET = (
    "odoo.addons.l10n_br_cnpj_search.wizard.partner_cnpj_search_wizard.requests.get"
)
CNPJ = "44356113000108"


@tagged("post_install", "-at_install")
class TestMinhaReceita(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.env["ir.config_parameter"].sudo().set_param(
            "l10n_br_cnpj_search.cnpj_provider", "minhareceita"
        )
        cls.webservice = cls.env["l10n_br_cnpj_search.webservice.abstract"]
        cls.cnae_main = cls._get_or_create(
            "l10n_br_fiscal.cnae",
            "4751-2/01",
            {
                "name": "Comercio varejista de equipamentos de informatica",
                "version": "2.0",
            },
        )
        cls.cnae_sec = cls._get_or_create(
            "l10n_br_fiscal.cnae",
            "4789-0/99",
            {"name": "Comercio varejista de outros produtos", "version": "2.0"},
        )
        cls.nature = cls._get_or_create(
            "l10n_br_fiscal.legal.nature",
            "2062",
            {"name": "Sociedade Empresaria Limitada"},
        )

    @classmethod
    def _get_or_create(cls, model, code, vals):
        masked = code.replace("-", "").replace("/", "")
        record = cls.env[model].search([("code_unmasked", "=", masked)], limit=1)
        return record or cls.env[model].create(dict(vals, code=code))

    def _data(self, **extra):
        data = {
            "razao_social": "ACME COMERCIO LTDA",
            "nome_fantasia": "ACME LOJA",
            "email": "CONTATO@ACME.COM",
            "logradouro": "RUA DAS FLORES",
            "complemento": "SALA 2",
            "bairro": "CENTRO",
            "numero": "10",
            "cep": "01001000",
            "ddd_telefone_1": "1133334444",
            "ddd_telefone_2": "11988887777",
            "uf": "SP",
            "municipio": "SAO PAULO",
            "capital_social": 5000.0,
            "cnae_fiscal": 4751201,
            "codigo_natureza_juridica": 2062,
            "cnaes_secundarios": [{"codigo": 4789099}, {"codigo": 9999999}],
        }
        data.update(extra)
        return data

    def test_provider_is_selectable_in_settings(self):
        """
        Given the module is installed
        When the settings selection is read and the provider is saved
        Then 'minhareceita' is offered and persisted as the CNPJ provider
        """
        selection = dict(
            self.env["res.config.settings"]._fields["cnpj_provider"].selection
        )
        self.assertEqual(selection.get("minhareceita"), "Minha Receita")
        settings = self.env["res.config.settings"].create(
            {"cnpj_provider": "minhareceita"}
        )
        settings.set_values()
        self.assertEqual(self.webservice.get_provider(), "minhareceita")

    def test_api_url_points_to_provider_with_cnpj(self):
        """
        Given the provider is minhareceita
        When the API url is requested for a CNPJ
        Then the url is the Minha Receita endpoint ending in that CNPJ
        """
        url = self.webservice.get_api_url(CNPJ)
        self.assertTrue(url.startswith("https://"))
        self.assertTrue(url.endswith(CNPJ))
        # control: another provider yields another endpoint
        self.env["ir.config_parameter"].sudo().set_param(
            "l10n_br_cnpj_search.cnpj_provider", "receitaws"
        )
        self.assertNotEqual(self.webservice.get_api_url(CNPJ), url)

    def test_headers_are_json_accept(self):
        """
        Given the provider is minhareceita
        When the request headers are requested through the generic dispatcher
        Then the Accept: application/json header is returned
        """
        self.assertEqual(self.webservice.get_headers(), {"Accept": "application/json"})

    def test_validate_ok_returns_payload(self):
        """
        Given a 200 response with a company payload
        When it is validated
        Then the payload is returned
        """
        response = mock.Mock(status_code=200)
        response.json.return_value = {"razao_social": "ACME"}
        self.assertEqual(self.webservice.validate(response), {"razao_social": "ACME"})

    def test_validate_error_payload_raises(self):
        """
        Given a 200 response whose body says status ERROR
        When it is validated
        Then a ValidationError carries the provider message
        """
        response = mock.Mock(status_code=200)
        response.json.return_value = {"status": "ERROR", "message": "Not found"}
        with self.assertRaisesRegex(ValidationError, "Not found"):
            self.webservice.validate(response)

    def test_validate_http_error_raises(self):
        """
        Given a 500 response
        When it is validated
        Then a ValidationError carries the HTTP reason
        """
        response = mock.Mock(status_code=500, reason="Server error")
        with self.assertRaisesRegex(ValidationError, "Server error"):
            self.webservice.validate(response)

    def test_import_data_maps_fields(self):
        """
        Given a full Minha Receita payload
        When it is imported
        Then names are title-cased, email lower-cased, phones, CNAEs,
        legal nature and state are mapped and unknown CNAEs are skipped
        """
        values = self.webservice.import_data(self._data())
        self.assertEqual(values["legal_name"], "Acme Comercio Ltda")
        self.assertEqual(values["name"], "Acme Loja")
        self.assertEqual(values["email"], "contato@acme.com")
        self.assertEqual(values["street_name"], "Rua Das Flores")
        self.assertEqual(values["street2"], "Sala 2")
        self.assertEqual(values["district"], "Centro")
        self.assertEqual(values["street_number"], "10")
        self.assertEqual(values["zip"], "01001000")
        self.assertEqual(values["phone"], "1133334444")
        self.assertEqual(values["mobile"], "11988887777")
        self.assertEqual(values["equity_capital"], 5000.0)
        self.assertEqual(values["cnae_main_id"], self.cnae_main.id)
        self.assertEqual(values["cnae_secondary_ids"], [self.cnae_sec.id])
        self.assertEqual(values["legal_nature_id"], self.nature.id)
        self.assertEqual(
            values["state_id"],
            self.env["res.country.state"]
            .search([("code", "=", "SP"), ("country_id.code", "=", "BR")], limit=1)
            .id,
        )

    def test_import_data_without_fantasy_name_uses_legal_name(self):
        """
        Given a payload with empty nome_fantasia
        When it is imported
        Then name falls back to the legal name
        """
        values = self.webservice.import_data(self._data(nome_fantasia=""))
        self.assertEqual(values["name"], "Acme Comercio Ltda")

    def test_import_data_without_codes_is_empty(self):
        """
        Given a payload without CNAE nor legal nature codes
        When it is imported
        Then those relations are False/empty instead of raising
        """
        data = self._data(cnaes_secundarios=[])
        data.pop("cnae_fiscal")
        data.pop("codigo_natureza_juridica")
        values = self.webservice.import_data(data)
        self.assertFalse(values["cnae_main_id"])
        self.assertFalse(values["legal_nature_id"])
        self.assertEqual(values["cnae_secondary_ids"], [])

    def test_partner_values_use_provider_url_and_headers(self):
        """
        Given the provider is minhareceita and the HTTP call is mocked
        When the wizard fetches the partner values for a CNPJ
        Then the request goes to the provider url with JSON headers and the
        imported values come back tagged with provider and CNPJ
        """
        response = mock.Mock(status_code=200)
        response.json.return_value = self._data()
        wizard_model = self.env["partner.search.wizard"]
        with mock.patch(WIZARD_REQUESTS_GET, return_value=response) as get:
            values = wizard_model._get_partner_values(CNPJ)
        args, kwargs = get.call_args
        self.assertTrue(args[0].endswith(CNPJ))
        self.assertEqual(kwargs["headers"], {"Accept": "application/json"})
        self.assertEqual(values["provider_name"], "minhareceita")
        self.assertEqual(values["cnpj_cpf"], CNPJ)
        self.assertEqual(values["legal_name"], "Acme Comercio Ltda")

    def test_wizard_updates_partner(self):
        """
        Given a company partner with a valid CNPJ
        When the CNPJ search wizard is opened and confirmed
        Then the partner receives the Minha Receita data
        """
        partner = self.env["res.partner"].create(
            {"name": "Antigo", "is_company": True, "cnpj_cpf": "44.356.113/0001-08"}
        )
        response = mock.Mock(status_code=200)
        response.json.return_value = self._data()
        with mock.patch(WIZARD_REQUESTS_GET, return_value=response):
            action = partner.action_open_cnpj_search_wizard()
            wizard = (
                self.env["partner.search.wizard"].with_context(**action["context"])
            ).create({})
            wizard.action_update_partner()
        self.assertEqual(partner.legal_name, "Acme Comercio Ltda")
        self.assertEqual(partner.name, "Acme Loja")
        self.assertEqual(partner.email, "contato@acme.com")
        self.assertEqual(partner.cnae_main_id, self.cnae_main)
        self.assertEqual(partner.legal_nature_id, self.nature)

    def test_wizard_requires_cnpj(self):
        """
        Given a partner without CNPJ
        When the CNPJ search is requested
        Then a UserError asks for the CNPJ
        """
        partner = self.env["res.partner"].create({"name": "Sem CNPJ"})
        with self.assertRaises(UserError):
            partner.action_open_cnpj_search_wizard()
