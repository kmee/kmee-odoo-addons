# Copyright (C) 2026 KMEE
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import os

from odoo.tests import TransactionCase, tagged

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return handle.read()


@tagged("post_install", "-at_install")
class TestDocumentExtractor(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.extractor = cls.env["l10n_br.document.extractor"]
        cls.company = cls.env.company
        cls.company.cnpj_cpf = "30.360.463/0001-25"

    def _extract(self, name="nfse_sp_texto.txt"):
        data, confidence, method = self.extractor.extract(fixture(name), self.company)
        return data, confidence

    def test_cnpj_emissor_com_dv(self):
        """O CNPJ do prestador (DV válido, diferente da empresa) é o emissor."""
        data, confidence = self._extract()
        self.assertEqual(data["issuer_cnpj"], "04391789000100")
        self.assertEqual(confidence["issuer_cnpj"], 1.0)
        self.assertEqual(data["destination_cnpj"], "30360463000125")

    def test_cnpj_dv_invalido_ignorado(self):
        """CNPJ com dígito verificador inválido não é extraído."""
        data, _conf, _method = self.extractor.extract(
            "CNPJ: 11.111.111/1111-11 Valor Total da Nota R$ 10,00",
            self.company,
        )
        self.assertNotIn("issuer_cnpj", data)

    def test_numero_e_verificacao(self):
        data, _conf = self._extract()
        self.assertEqual(data["document_number"], "00012345")
        self.assertEqual(data["verify_code"], "ABCD-EFGH")
        self.assertEqual(data["service_code"], "01.05")

    def test_data_emissao(self):
        data, _conf = self._extract()
        self.assertEqual(data["document_date"], "2026-07-15")

    def test_valores_e_retencoes(self):
        data, _conf = self._extract()
        self.assertEqual(data["amount_untaxed"], 10000.00)
        self.assertEqual(data["amount_total"], 9385.00)
        self.assertEqual(data["issqn_base"], 10000.00)
        self.assertEqual(data["issqn_value"], 200.00)
        self.assertEqual(data["issqn_wh_value"], 0.00)
        self.assertEqual(data["irpj_wh_value"], 150.00)
        self.assertEqual(data["csll_wh_value"], 100.00)
        self.assertEqual(data["cofins_wh_value"], 300.00)
        self.assertEqual(data["pis_wh_value"], 65.00)

    def test_reconciliacao_eleva_confianca(self):
        """untaxed - retenções == total -> confiança máxima nos totais."""
        _data, confidence = self._extract()
        self.assertEqual(confidence["amount_total"], 1.0)
        self.assertEqual(confidence["amount_untaxed"], 1.0)

    def test_chave_44_detectada(self):
        text = (
            "DANFE Documento Auxiliar\n"
            "Chave de acesso: 3520 0159 5943 1500 0157 5500 1000 0000 0120 "
            "6277 7161\nValor Total R$ 10,00"
        )
        data, _conf, _method = self.extractor.extract(text, self.company)
        self.assertEqual(
            data["document_key"],
            "35200159594315000157550010000000012062777161",
        )
