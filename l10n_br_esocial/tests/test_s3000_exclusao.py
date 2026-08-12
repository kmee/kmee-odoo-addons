# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import HAS_ESOCIALLIB, RECIBO_S1200, ESocialCicloCommon


@tagged("post_install", "-at_install")
class TestS3000Exclusao(ESocialCicloCommon):
    """S-3000: exclusão de evento já aceito pelo eSocial."""

    def _evento_s1200_aceito(self):
        payslip = self._criar_payslip()
        payslip.action_esocial_gerar_s1200()
        evento = payslip.l10n_br_esocial_s1200_id.evento_id
        evento.write({"state": "success", "nr_recibo": RECIBO_S1200})
        return evento

    def _criar_s3000(self, evento, **kwargs):
        vals = {
            "evento_origem_id": evento.id,
            "company_id": self.company.id,
            "per_apur": evento.per_apur,
            "ind_apuracao": "1",
            "cpf_trab": self.cpf_employee,
        }
        vals.update(kwargs)
        return self.env["l10n_br.esocial.s3000"].create(vals)

    # ── Pré-condições ──────────────────────────────────────────────────────

    def test_exige_evento_aceito(self):
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        s3000 = self._criar_s3000(evento)
        with self.assertRaises(UserError):
            s3000.action_gerar_evento()

    def test_exige_recibo(self):
        evento = self._criar_evento("S-1200", per_apur="2024-03")
        s3000 = self._criar_s3000(evento)
        with self.assertRaises(UserError):
            s3000.action_gerar_evento()

    def test_recibo_em_formato_invalido(self):
        evento = self._criar_evento(
            "S-1200", per_apur="2024-03", nr_recibo="1.2.202403.0001"
        )
        s3000 = self._criar_s3000(evento)
        with self.assertRaises(ValidationError):
            s3000.action_gerar_evento()

    def test_periodico_exige_competencia(self):
        evento = self._criar_evento("S-1200", nr_recibo=RECIBO_S1200)
        s3000 = self._criar_s3000(evento, per_apur=False)
        with self.assertRaises(UserError):
            s3000.action_gerar_evento()

    def test_evento_com_trabalhador_exige_cpf(self):
        evento = self._criar_evento(
            "S-1200", per_apur="2024-03", nr_recibo=RECIBO_S1200
        )
        s3000 = self._criar_s3000(evento, cpf_trab=False)
        with self.assertRaises(UserError):
            s3000.action_gerar_evento()

    def test_exclusao_duplicada_bloqueada(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        evento = self._evento_s1200_aceito()
        self._criar_s3000(evento).action_gerar_evento()
        segundo = self._criar_s3000(evento)
        with self.assertRaises(UserError):
            segundo.action_gerar_evento()

    # ── Herança de dados do evento de origem ───────────────────────────────

    def test_onchange_herda_competencia_e_cpf(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        evento = self._evento_s1200_aceito()
        s3000 = self.env["l10n_br.esocial.s3000"].new(
            {"evento_origem_id": evento.id, "company_id": self.company.id}
        )
        s3000._onchange_evento_origem_id()
        self.assertEqual(s3000.per_apur, "2024-03")
        self.assertEqual(s3000.ind_apuracao, "1")
        self.assertEqual(s3000.cpf_trab, self.cpf_employee)

    def test_tipo_e_recibo_sao_do_evento(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        evento = self._evento_s1200_aceito()
        s3000 = self._criar_s3000(evento)
        self.assertEqual(s3000.tp_evento, "S-1200")
        self.assertEqual(s3000.nr_rec_evt, RECIBO_S1200)

    # ── Geração e propagação ───────────────────────────────────────────────

    def test_gera_evento_de_exclusao(self):
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        origem = self._evento_s1200_aceito()
        s3000 = self._criar_s3000(origem, motivo="Rubrica classificada errada")
        evento = s3000.action_gerar_evento()
        self.assertEqual(evento.tipo, "S-3000")
        self.assertEqual(evento.operacao, "E")
        self.assertEqual(evento.evento_excluido_id, origem)
        raiz = etree.fromstring(evento.xml_envio.encode("utf-8"))
        valores = {
            elemento.tag.rsplit("}", 1)[-1]: (elemento.text or "").strip()
            for elemento in raiz.iter()
        }
        self.assertEqual(valores["tpEvento"], "S-1200")
        self.assertEqual(valores["nrRecEvt"], RECIBO_S1200)
        self.assertEqual(valores["cpfTrab"], self.cpf_employee)
        self.assertEqual(valores["perApur"], "2024-03")

    def test_aceite_marca_origem_como_excluida(self):
        """Aceite do S-3000 tem de refletir no evento excluído."""
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        origem = self._evento_s1200_aceito()
        evento = self._criar_s3000(origem).action_gerar_evento()
        evento.registrar_aceite(nr_recibo="1.2.0000000000000055555")
        self.assertEqual(evento.state, "success")
        self.assertEqual(origem.state, "excluded")

    def test_motivo_nao_vai_para_o_xml(self):
        """O motivo é auditoria interna, não campo do leiaute."""
        if not HAS_ESOCIALLIB:
            self.skipTest("esociallib não instalada")
        origem = self._evento_s1200_aceito()
        s3000 = self._criar_s3000(origem, motivo="segredo interno")
        evento = s3000.action_gerar_evento()
        self.assertNotIn("segredo interno", evento.xml_envio)
