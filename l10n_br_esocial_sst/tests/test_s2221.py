# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import unittest

from lxml import etree

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import HAS_ESOCIALLIB, EsocialSstCommon

NS_2221 = "http://www.esocial.gov.br/schema/evt/evtToxic/v_S_01_03_00"


@tagged("post_install", "-at_install")
class TestS2221(EsocialSstCommon):
    """RS-37: exame toxicológico do motorista profissional."""

    def _cria_evento(self, **kwargs):
        valores = {
            "company_id": self.company.id,
            "employee_id": self.employee.id,
            "dt_exame": self.hoje,
            "cnpj_lab": "12.345.678/0001-99",
            "cod_seq_exame": "AB123456789",
            "nm_med": "Dr. Toxicologista",
            "nr_crm": "123456",
            "uf_crm": "MG",
        }
        valores.update(kwargs)
        return self.env["l10n_br.esocial.s2221"].create(valores)

    def test_cnpj_do_laboratorio_invalido(self):
        with self.assertRaises(ValidationError):
            self._cria_evento(cnpj_lab="123")

    def test_codigo_do_exame_invalido(self):
        with self.assertRaises(ValidationError):
            self._cria_evento(cod_seq_exame="123456789")

    def test_dicionario_do_evento(self):
        evento = self._cria_evento()
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["cnpj_lab"], "12345678000199")
        self.assertEqual(dados["cod_seq_exame"], "AB123456789")
        self.assertEqual(dados["matricula"], "MAT001")

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_xml_do_evento(self):
        evento = self._cria_evento()
        xml = evento._gerar_xml()
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        ns = {"e": NS_2221}
        self.assertEqual(
            root.find(".//e:toxicologico/e:cnpjLab", ns).text, "12345678000199"
        )
