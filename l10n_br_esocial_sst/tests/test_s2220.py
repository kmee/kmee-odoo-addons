# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import unittest

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import HAS_ESOCIALLIB, EsocialSstCommon

NS_2220 = "http://www.esocial.gov.br/schema/evt/evtMonit/v_S_01_03_00"


@tagged("post_install", "-at_install")
class TestS2220(EsocialSstCommon):
    """RS-15: ASO transmitido pelo S-2220."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.medico = cls.env["l10n_br.sst.responsavel"].create(
            {
                "name": "Dra. Coordenadora",
                "cpf": "076.166.929-41",
                "ide_oc": "1",
                "nr_oc": "654321",
                "uf_oc": "MG",
            }
        )
        cls.pcmso = cls.env["l10n_br.sst.pcmso"].create(
            {
                "name": "PCMSO 2026",
                "medico_coordenador_id": cls.medico.id,
                "date_from": cls.hoje,
                "state": "vigente",
            }
        )
        cls.procedimento = cls.env["l10n_br.esocial.procedimento.diagnostico"].search(
            [], limit=1
        )

    def _aso_concluido(self, tipo="0"):
        exame = self.env["hr.employee.medical.examination"].l10n_br_gerar_aso(
            self.employee, tipo, date=self.hoje
        )
        self.env["l10n_br.sst.exame.complementar"].create(
            {
                "examination_id": exame.id,
                "procedimento_id": self.procedimento.id,
                "date": self.hoje,
                "ord_exame": "1",
                "ind_result": "1",
            }
        )
        exame.write(
            {
                "l10n_br_resultado": "1",
                "l10n_br_medico_nome": "Dr. Examinador",
                "l10n_br_crm": "123456",
                "l10n_br_uf_crm": "MG",
            }
        )
        exame.to_done()
        return exame

    def test_concluir_aso_prepara_o_evento(self):
        exame = self._aso_concluido()
        self.assertTrue(exame.l10n_br_s2220_id)

    def test_nao_duplica_evento(self):
        exame = self._aso_concluido()
        primeiro = exame.l10n_br_s2220_id
        exame.action_gerar_s2220()
        self.assertEqual(exame.l10n_br_s2220_id, primeiro)

    def test_validacao_exige_exame_complementar(self):
        exame = self.env["hr.employee.medical.examination"].l10n_br_gerar_aso(
            self.employee, "0", date=self.hoje
        )
        exame.write(
            {
                "l10n_br_resultado": "1",
                "l10n_br_medico_nome": "Dr. Examinador",
            }
        )
        evento = self.env["l10n_br.esocial.s2220"].gerar_para_exame(exame)
        with self.assertRaises(UserError):
            evento._validar_antes_do_envio()

    def test_dicionario_do_evento(self):
        exame = self._aso_concluido()
        dados = exame.l10n_br_s2220_id._to_esociallib_dict()
        self.assertEqual(dados["tp_exame_ocup"], 0)
        self.assertEqual(dados["res_aso"], 1)
        self.assertEqual(dados["nm_med"], "Dr. Examinador")
        self.assertEqual(dados["nr_crm"], "123456")
        self.assertEqual(len(dados["exames"]), 1)
        self.assertEqual(dados["nm_resp"], "Dra. Coordenadora")

    def test_demissional_usa_o_codigo_nove(self):
        """O leiaute usa 9 para o demissional, e não 8."""
        exame = self._aso_concluido(tipo="9")
        dados = exame.l10n_br_s2220_id._to_esociallib_dict()
        self.assertEqual(dados["tp_exame_ocup"], 9)

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_xml_do_evento(self):
        exame = self._aso_concluido()
        xml = exame.l10n_br_s2220_id._gerar_xml()
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        ns = {"e": NS_2220}
        self.assertEqual(root.find(".//e:exMedOcup/e:tpExameOcup", ns).text, "0")
        self.assertEqual(root.find(".//e:aso/e:resAso", ns).text, "1")
        self.assertEqual(root.find(".//e:medico/e:nmMed", ns).text, "Dr. Examinador")
