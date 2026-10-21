# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import unittest

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import HAS_ESOCIALLIB, EsocialSstCommon

NS_2240 = "http://www.esocial.gov.br/schema/evt/evtExpRisco/v_S_01_03_00"


@tagged("post_install", "-at_install")
class TestS2240(EsocialSstCommon):
    """RS-16 e RS-17: S-2240 com epiEpc, validações e geração em massa."""

    def _cria_s2240(self):
        self._entrega_epi()
        return self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje
        )

    # ── Montagem ────────────────────────────────────────────────────────────

    def test_gerar_para_contrato(self):
        evento = self._cria_s2240()
        self.assertEqual(evento.employee_id, self.employee)
        self.assertEqual(evento.ambiente_id, self.ambiente)
        self.assertIn(self.risco, evento.risco_ids)
        self.assertIn(self.responsavel, evento.responsavel_ids)

    def test_sem_ambiente_nao_gera(self):
        self.contract.l10n_br_sst_ambiente_id = False
        evento = self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje
        )
        self.assertFalse(evento)

    def test_dsc_ativ_des_vem_do_ambiente(self):
        evento = self._cria_s2240()
        self.assertEqual(evento.dsc_ativ_des, "Operação de envasadora automática.")

    def test_ag_noc_com_epi_entregue(self):
        evento = self._cria_s2240()
        ag_noc = evento._to_ag_noc(self.risco)
        self.assertEqual(ag_noc["cod_ag_noc"], "02.01.001")
        self.assertEqual(ag_noc["utiliz_epi"], 2)
        self.assertEqual(ag_noc["efic_epi"], "S")
        self.assertEqual(ag_noc["epi"], [{"doc_aval": "31000"}])
        self.assertEqual(ag_noc["higienizacao"], "S")

    def test_ag_noc_ausencia_de_risco(self):
        risco = self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ausencia.id,
                "laudo_id": self.laudo.id,
                "date_from": self.hoje,
            }
        )
        evento = self._cria_s2240()
        ag_noc = evento._to_ag_noc(risco)
        self.assertEqual(ag_noc["utiliz_epc"], 0)
        self.assertEqual(ag_noc["utiliz_epi"], 0)
        self.assertNotIn("epi", ag_noc)

    # ── Validações antes do envio (RS-17) ───────────────────────────────────

    def test_valida_sem_epi_entregue(self):
        """Declarar uso de EPI sem entrega válida é erro antes do envio."""
        evento = self.env["l10n_br.esocial.s2240"].gerar_para_contrato(
            self.contract, data=self.hoje
        )
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_sem_responsavel(self):
        evento = self._cria_s2240()
        evento.responsavel_ids = [(5, 0, 0)]
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_sem_risco(self):
        evento = self._cria_s2240()
        evento.risco_ids = [(5, 0, 0)]
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_ausencia_com_outros_riscos(self):
        evento = self._cria_s2240()
        risco_ausencia = self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ausencia.id,
                "date_from": self.hoje,
            }
        )
        evento.risco_ids = [(4, risco_ausencia.id)]
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_epc_sem_eficacia(self):
        evento = self._cria_s2240()
        self.risco.write({"utiliz_epc": "2", "efic_epc": False})
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_epi_sem_eficacia(self):
        evento = self._cria_s2240()
        self.risco.efic_epi = False
        with self.assertRaises(UserError):
            evento.action_validar()

    def test_valida_ok(self):
        evento = self._cria_s2240()
        self.assertTrue(evento.action_validar())

    # ── Geração em massa ────────────────────────────────────────────────────

    def test_gerar_em_massa_pelo_laudo(self):
        self._entrega_epi()
        acao = self.laudo.action_gerar_s2240()
        eventos = self.env["l10n_br.esocial.s2240"].search(acao["domain"])
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos.employee_id, self.employee)

    def test_gerar_em_massa_nao_duplica(self):
        self._entrega_epi()
        self.laudo.action_gerar_s2240()
        acao = self.laudo.action_gerar_s2240()
        self.assertFalse(self.env["l10n_br.esocial.s2240"].search(acao["domain"]))

    def test_laudo_em_rascunho_nao_gera(self):
        laudo = self.env["l10n_br.sst.laudo"].create(
            {"name": "PGR rascunho", "date_from": self.hoje}
        )
        with self.assertRaises(UserError):
            laudo.action_gerar_s2240()

    # ── XML ─────────────────────────────────────────────────────────────────

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_xml_do_evento(self):
        evento = self._cria_s2240()
        xml = evento._gerar_xml()
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        ns = {"e": NS_2240}
        self.assertEqual(root.find(".//e:agNoc/e:codAgNoc", ns).text, "02.01.001")
        self.assertEqual(root.find(".//e:epcEpi/e:epi/e:docAval", ns).text, "31000")
        self.assertEqual(root.find(".//e:infoAmb/e:dscSetor", ns).text, "PRODUCAO")
        self.assertEqual(root.find(".//e:respReg/e:cpfResp", ns).text, "07616692941")
        self.assertEqual(root.find(".//e:ideVinculo/e:cpfTrab", ns).text, "07616692941")

    @unittest.skipUnless(HAS_ESOCIALLIB, "esociallib não instalada")
    @mute_logger("odoo.addons.l10n_br_esocial.models.intermediarios.base_intermediario")
    def test_evento_preenche_id_evento(self):
        """O ciclo do PR do S-1005 vale para o SST: sem Id não casa o retorno."""
        evento = self._cria_s2240()
        registro = evento.action_gerar_evento()
        self.assertTrue(registro.id_evento)
        self.assertEqual(registro.tipo, "S-2240")
