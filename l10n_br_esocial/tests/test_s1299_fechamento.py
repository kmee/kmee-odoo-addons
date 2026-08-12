# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import HAS_ESOCIALLIB, RECIBO_S1200, RECIBO_S1299, ESocialCicloCommon


@tagged("post_install", "-at_install")
class TestS1299Fechamento(ESocialCicloCommon):
    """S-1299/S-1298: fechamento e reabertura dos eventos periódicos."""

    def _criar_s1299(self, **kwargs):
        vals = {
            "per_apur": "2024-03",
            "ind_apuracao": "1",
            "company_id": self.company.id,
        }
        vals.update(kwargs)
        return self.env["l10n_br.esocial.s1299"].create(vals)

    def _criar_s1298(self, **kwargs):
        vals = {
            "per_apur": "2024-03",
            "ind_apuracao": "1",
            "company_id": self.company.id,
        }
        vals.update(kwargs)
        return self.env["l10n_br.esocial.s1298"].create(vals)

    # ── Declaração de conteúdo ─────────────────────────────────────────────

    def test_evt_remun_reflete_s1200_aceito(self):
        self._criar_evento("S-1200", per_apur="2024-03", nr_recibo=RECIBO_S1200)
        s1299 = self._criar_s1299()
        self.assertEqual(s1299.evt_remun, "S")
        self.assertEqual(s1299.evt_pgtos, "N")

    def test_evt_pgtos_reflete_s1210_aceito(self):
        self._criar_evento("S-1200", per_apur="2024-03")
        self._criar_evento("S-1210", per_apur="2024-03")
        s1299 = self._criar_s1299()
        self.assertEqual(s1299.evt_pgtos, "S")

    def test_competencia_de_outra_empresa_nao_conta(self):
        outra = self.env["res.company"].create({"name": "Outra Empresa eSocial"})
        self._criar_evento("S-1200", per_apur="2024-03", company_id=outra.id)
        s1299 = self._criar_s1299()
        self.assertEqual(s1299.evt_remun, "N")

    # ── Pendências (o coração do fechamento) ───────────────────────────────

    def test_pendencia_bloqueia_fechamento(self):
        """Evento periódico sem aceite impede o fechamento da competência."""
        self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        s1299 = self._criar_s1299()
        self.assertEqual(s1299.pendencia_count, 1)
        with self.assertRaises(UserError) as erro:
            s1299.action_gerar_evento()
        self.assertIn("S-1200", str(erro.exception))
        self.assertFalse(s1299.evento_id)

    def test_pendencia_em_erro_bloqueia(self):
        self._criar_evento("S-1200", state="error", per_apur="2024-03")
        s1299 = self._criar_s1299()
        with self.assertRaises(UserError):
            s1299.action_gerar_evento()

    def test_evento_excluido_nao_e_pendencia(self):
        """Evento excluído com S-3000 sai da conta de pendências."""
        self._criar_evento("S-1200", state="excluded", per_apur="2024-03")
        s1299 = self._criar_s1299()
        self.assertEqual(s1299.pendencia_count, 0)

    def test_pendencia_de_outra_competencia_nao_bloqueia(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        self._criar_evento("S-1200", state="sent", per_apur="2024-02")
        self._criar_evento("S-1200", per_apur="2024-03")
        s1299 = self._criar_s1299()
        self.assertEqual(s1299.pendencia_count, 0)
        self.assertTrue(s1299.action_gerar_evento())

    def test_declara_remuneracao_sem_s1200_aceito(self):
        """Declarar 'possui remuneração' sem S-1200 aceito é inconsistente."""
        s1299 = self._criar_s1299()
        s1299.evt_remun = "S"
        with self.assertRaises(UserError):
            s1299.action_gerar_evento()

    def test_fecha_competencia_sem_movimento(self):
        """Competência sem evento periódico fecha declarando 'N'."""
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        s1299 = self._criar_s1299()
        evento = s1299.action_gerar_evento()
        self.assertEqual(evento.tipo, "S-1299")
        self.assertEqual(evento.per_apur, "2024-03")

    # ── Refechamento e reabertura ──────────────────────────────────────────

    def test_refechamento_exige_reabertura(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        self._criar_evento("S-1299", per_apur="2024-03", nr_recibo=RECIBO_S1299)
        s1299 = self._criar_s1299()
        with self.assertRaises(UserError) as erro:
            s1299.action_gerar_evento()
        self.assertIn("S-1298", str(erro.exception))

    def test_refechamento_liberado_apos_reabertura(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        fechamento = self._criar_evento(
            "S-1299", per_apur="2024-03", nr_recibo=RECIBO_S1299
        )
        reabertura = self._criar_evento("S-1298", per_apur="2024-03")
        # É a reabertura POSTERIOR ao fechamento que autoriza fechar de novo.
        self.assertGreater(reabertura.id, fechamento.id)
        s1299 = self._criar_s1299()
        self.assertTrue(s1299.action_gerar_evento())

    def test_reabertura_exige_fechamento_aceito(self):
        s1298 = self._criar_s1298()
        self.assertFalse(s1298.fechamento_evento_id)
        with self.assertRaises(UserError):
            s1298.action_gerar_evento()

    def test_reabertura_com_fechamento_aceito(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        fechamento = self._criar_evento(
            "S-1299", per_apur="2024-03", nr_recibo=RECIBO_S1299
        )
        s1298 = self._criar_s1298()
        self.assertEqual(s1298.fechamento_evento_id, fechamento)
        evento = s1298.action_gerar_evento()
        self.assertEqual(evento.tipo, "S-1298")

    # ── Competência e XML ──────────────────────────────────────────────────

    def test_competencia_anual_para_13o(self):
        s1299 = self._criar_s1299(per_apur="2024", ind_apuracao="2")
        self.assertEqual(s1299.per_apur, "2024")

    def test_competencia_anual_recusada_no_mensal(self):
        with self.assertRaises(ValidationError):
            self._criar_s1299(per_apur="2024", ind_apuracao="1")

    def test_xml_do_fechamento(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        self._criar_evento("S-1200", per_apur="2024-03")
        self._criar_evento("S-1210", per_apur="2024-03")
        s1299 = self._criar_s1299(trans_dctf_web=True)
        evento = s1299.action_gerar_evento()
        raiz = etree.fromstring(evento.xml_envio.encode("utf-8"))
        valores = {
            elemento.tag.rsplit("}", 1)[-1]: (elemento.text or "").strip()
            for elemento in raiz.iter()
        }
        self.assertEqual(valores["perApur"], "2024-03")
        self.assertEqual(valores["indApuracao"], "1")
        self.assertEqual(valores["evtRemun"], "S")
        self.assertEqual(valores["evtPgtos"], "S")
        self.assertEqual(valores["evtComProd"], "N")
        self.assertEqual(valores["transDCTFWeb"], "S")

    def test_xml_da_reabertura(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        self._criar_evento("S-1299", per_apur="2024-03", nr_recibo=RECIBO_S1299)
        s1298 = self._criar_s1298()
        evento = s1298.action_gerar_evento()
        raiz = etree.fromstring(evento.xml_envio.encode("utf-8"))
        self.assertIn("evtReabreEvPer", raiz[0].tag)
