# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import unittest
from datetime import date

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import HAS_ESOCIALLIB, EsocialSstCommon

NS_2210 = "http://www.esocial.gov.br/schema/evt/evtCAT/v_S_01_03_00"


@tagged("post_install", "-at_install")
class TestS2210(EsocialSstCommon):
    """RS-14: CAT transmitida pelo S-2210."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.acidente = cls.env["l10n_br.sst.acidente"].create(
            {
                "employee_id": cls.employee.id,
                "date_acidente": date(2026, 6, 10),
                "hora_acidente": "1430",
                "hrs_trab_antes_acid": "0330",
                "tp_acid": "1",
                "situacao_geradora_id": cls.env["l10n_br.esocial.situacao.geradora"]
                .search([], limit=1)
                .id,
                "parte_corpo_id": cls.env["l10n_br.esocial.parte.corpo"]
                .search([], limit=1)
                .id,
                "agente_causador_id": cls.env["l10n_br.esocial.agente.causador"]
                .search([], limit=1)
                .id,
                "natureza_lesao_id": cls.env["l10n_br.esocial.natureza.lesao"]
                .search([], limit=1)
                .id,
                "cid_id": cls.env["l10n_br.esocial.cid"].search([], limit=1).id,
                "dsc_lograd": "RUA DAS FLORES",
                "nr_lograd": "100",
                "bairro_local": "CENTRO",
                "cep_local": "37500000",
                "date_atendimento": date(2026, 6, 10),
                "hora_atendimento": "1500",
                "dur_trat": 15,
                "nm_emit": "Dr. Plantonista",
                "ide_oc_emit": "1",
                "nr_oc_emit": "123456",
                "uf_oc_emit": "MG",
                "houve_afastamento": True,
                "ind_afast": "S",
            }
        )
        cls.acidente.action_registrar()
        cls.cat = cls.acidente.cat_ids

    def test_emitir_prepara_o_evento(self):
        self.cat.action_emitir()
        self.assertTrue(self.cat.s2210_id)
        self.assertEqual(self.cat.s2210_id.employee_id, self.employee)

    def test_validacao_exige_atestado(self):
        self.acidente.nm_emit = False
        evento = self.cat.action_gerar_s2210()
        with self.assertRaises(UserError):
            evento._validar_antes_do_envio()

    def test_tipica_exige_horas_trabalhadas(self):
        evento = self.cat.action_gerar_s2210()
        self.acidente.hrs_trab_antes_acid = False
        with self.assertRaisesRegex(UserError, "hrsTrabAntesAcid"):
            evento._validar_antes_do_envio()
        self.acidente.hrs_trab_antes_acid = "2530"
        evento._validar_antes_do_envio()

    def test_trajeto_exige_horas_trabalhadas(self):
        evento = self.cat.action_gerar_s2210()
        self.acidente.write({"tp_acid": "3", "hrs_trab_antes_acid": False})
        with self.assertRaisesRegex(UserError, "hrsTrabAntesAcid"):
            evento._validar_antes_do_envio()
        self.acidente.hrs_trab_antes_acid = "0330"
        evento._validar_antes_do_envio()

    def test_trajeto_antes_de_20_07_2022_dispensa_horas_trabalhadas(self):
        """Só o trajeto tem marco de data no leiaute; a típica sempre exige."""
        evento = self.cat.action_gerar_s2210()
        self.acidente.write(
            {
                "tp_acid": "3",
                "date_acidente": date(2022, 7, 19),
                "hrs_trab_antes_acid": False,
            }
        )
        evento._validar_antes_do_envio()
        self.acidente.tp_acid = "1"
        with self.assertRaisesRegex(UserError, "hrsTrabAntesAcid"):
            evento._validar_antes_do_envio()

    def test_doenca_recusa_horas_trabalhadas(self):
        evento = self.cat.action_gerar_s2210()
        self.acidente.write({"tp_acid": "2", "hrs_trab_antes_acid": False})
        evento._validar_antes_do_envio()
        with self.assertRaises(ValidationError):
            self.acidente.hrs_trab_antes_acid = "0300"

    def test_reabertura_sem_recibo_de_origem(self):
        self.cat.action_emitir()
        reabertura = self.acidente._criar_cat("2")
        reabertura.nr_rec_cat_orig = False
        evento = reabertura.action_gerar_s2210()
        with self.assertRaises(UserError):
            evento._validar_antes_do_envio()

    def test_dicionario_do_evento(self):
        evento = self.cat.action_gerar_s2210()
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["dt_acid"], "2026-06-10")
        self.assertEqual(dados["hr_acid"], "1430")
        self.assertEqual(dados["hrs_trab_antes_acid"], "0330")
        self.assertEqual(dados["tp_acid"], 1)
        self.assertEqual(dados["tp_cat"], 1)
        self.assertEqual(dados["ind_cat_obito"], "N")
        self.assertEqual(dados["houve_afast"], "S")
        self.assertEqual(dados["nm_emit"], "Dr. Plantonista")
        self.assertEqual(dados["cpf_trab"], "07616692941")

    def test_obito_leva_data_do_obito(self):
        self.acidente.write({"houve_obito": True, "date_obito": date(2026, 6, 11)})
        evento = self.cat.action_gerar_s2210()
        dados = evento._to_esociallib_dict()
        self.assertEqual(dados["ind_cat_obito"], "S")
        self.assertEqual(dados["dt_obito"], "2026-06-11")

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_xml_do_evento(self):
        evento = self.cat.action_gerar_s2210()
        xml = evento._gerar_xml()
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        ns = {"e": NS_2210}
        self.assertEqual(root.find(".//e:cat/e:dtAcid", ns).text, "2026-06-10")
        self.assertEqual(root.find(".//e:cat/e:tpCat", ns).text, "1")
        self.assertEqual(
            root.find(".//e:emitente/e:nmEmit", ns).text, "Dr. Plantonista"
        )

    def test_recibo_volta_para_a_cat(self):
        """O recibo do eSocial chega à CAT e libera a CAT de reabertura."""
        self.cat.action_emitir()
        evento = self.env["l10n_br.esocial.evento"].create(
            {"tipo": "S-2210", "company_id": self.cat.company_id.id}
        )
        evento.registrar_aceite(nr_recibo="1.1.1234567890123456789")
        self.cat.s2210_id.evento_id = evento
        self.env["l10n_br.sst.cat"]._atualizar_recibo()
        self.assertEqual(self.cat.state, "transmitida")
        self.assertEqual(self.cat.numero_recibo, "1.1.1234567890123456789")
        reabertura = self.acidente._criar_cat("2")
        self.assertEqual(reabertura.nr_rec_cat_orig, "1.1.1234567890123456789")
