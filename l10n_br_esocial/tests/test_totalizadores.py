# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock

from odoo.tests import tagged

from .common import (
    RECIBO_S1200,
    RECIBO_S1299,
    ESocialCicloCommon,
    FakeEventoResult,
    FakeLoteResult,
    retorno_s5001,
    retorno_s5011,
    retorno_s5012,
)


@tagged("post_install", "-at_install")
class TestTotalizadores(ESocialCicloCommon):
    """Consumo dos totalizadores devolvidos e conferência da competência."""

    def _consumir(self, evento, retorno_xml):
        """Simula o aceite do evento com o retorno do governo."""
        evento.registrar_aceite(nr_recibo=RECIBO_S1200, retorno_xml=retorno_xml)
        return evento.totalizador_ids

    # ── Persistência ───────────────────────────────────────────────────────

    def test_s5001_persiste_ligado_ao_evento(self):
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        totalizadores = self._consumir(evento, retorno_s5001(self.cpf_employee))
        self.assertEqual(len(totalizadores), 1)
        totalizador = totalizadores
        self.assertEqual(totalizador.tipo, "S-5001")
        self.assertEqual(totalizador.evento_id, evento)
        self.assertEqual(totalizador.per_apur, "2024-03")
        self.assertEqual(totalizador.nr_rec_arq_base, RECIBO_S1200)
        self.assertEqual(totalizador.cpf_trab, self.cpf_employee)
        self.assertTrue(totalizador.xml)

    def test_s5001_resolve_trabalhador_pelo_cpf(self):
        """O totalizador chega com CPF: precisa casar com o empregado."""
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        totalizador = self._consumir(evento, retorno_s5001(self.cpf_employee))
        self.assertEqual(totalizador.employee_id, self.employee)

    def test_s5001_cpf_desconhecido_nao_quebra(self):
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        totalizador = self._consumir(evento, retorno_s5001("99988877766"))
        self.assertFalse(totalizador.employee_id)
        self.assertEqual(totalizador.cpf_trab, "99988877766")

    def test_s5001_linhas_com_valores(self):
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        totalizador = self._consumir(evento, retorno_s5001(self.cpf_employee))
        grupos = set(totalizador.linha_ids.mapped("grupo"))
        self.assertEqual(grupos, {"info_cp_calc", "base_cs", "calc_terc"})
        base = totalizador.linha_ids.filtered(lambda l: l.grupo == "base_cs")
        self.assertAlmostEqual(base.valor, 3000.0, places=2)
        self.assertEqual(base.matricula, "MAT001")
        self.assertEqual(base.cod_categ, "101")
        self.assertEqual(base.cod_lotacao, "LOT001")
        desc = totalizador.linha_ids.filtered(
            lambda l: l.grupo == "info_cp_calc" and l.descricao == "vrDescSeg"
        )
        self.assertAlmostEqual(desc.valor, 330.0, places=2)

    def test_s5011_consolidado(self):
        evento = self._criar_evento("S-1299", state="sent", per_apur="2024-03")
        evento.registrar_aceite(nr_recibo=RECIBO_S1299, retorno_xml=retorno_s5011())
        totalizador = evento.totalizador_ids
        self.assertEqual(totalizador.tipo, "S-5011")
        self.assertEqual(totalizador.ind_exist_info, "1")
        patronal = totalizador.linha_ids.filtered(
            lambda l: l.grupo == "cr_contrib" and l.codigo == "115101"
        )
        self.assertAlmostEqual(patronal.valor, 600.0, places=2)

    def test_reconsulta_nao_duplica(self):
        """Consultar o lote de novo substitui os totalizadores, não soma."""
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        self._consumir(evento, retorno_s5001(self.cpf_employee))
        primeiros = evento.totalizador_ids.ids
        self._consumir(evento, retorno_s5001(self.cpf_employee))
        self.assertEqual(len(evento.totalizador_ids), 1)
        self.assertNotEqual(evento.totalizador_ids.ids, primeiros)

    def test_retorno_sem_totalizador(self):
        evento = self._criar_evento("S-1000", state="sent")
        evento.registrar_aceite(
            nr_recibo=RECIBO_S1200,
            retorno_xml="<evento Id='ID1'><retornoEvento/></evento>",
        )
        self.assertEqual(len(evento.totalizador_ids), 0)
        self.assertEqual(evento.state, "success")

    def test_retorno_ilegivel_nao_quebra_o_aceite(self):
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        evento.registrar_aceite(nr_recibo=RECIBO_S1200, retorno_xml="nao e xml <<<")
        self.assertEqual(evento.state, "success")
        self.assertEqual(len(evento.totalizador_ids), 0)

    # ── Retorno via lote (mock da esociallib) ──────────────────────────────

    def test_consulta_lote_persiste_totalizador(self):
        """O caminho real: consulta do lote traz o retorno com o totalizador."""
        evento = self._criar_evento(
            "S-1200", state="sent", per_apur="2024-03", id_evento="IDBASE1200"
        )
        lote = self.env["l10n_br.esocial.lote"].create(
            {"company_id": self.company.id, "state": "sent", "protocolo": "PROTO1"}
        )
        evento.lote_id = lote.id
        resultado = FakeLoteResult(
            status="processado",
            eventos=[
                FakeEventoResult(
                    event_id="IDBASE1200",
                    aceito=True,
                    nr_recibo=RECIBO_S1200,
                    retorno_xml=retorno_s5001(self.cpf_employee),
                )
            ],
        )
        with mock.patch.object(
            type(lote), "_get_certificate", return_value=(b"pfx", "senha")
        ), mock.patch(
            "odoo.addons.l10n_br_esocial.models.esocial_lote.consultar_lote",
            return_value=resultado,
        ):
            lote.action_consultar()
        self.assertEqual(evento.state, "success")
        self.assertEqual(evento.nr_recibo, RECIBO_S1200)
        self.assertEqual(len(evento.totalizador_ids), 1)
        self.assertEqual(evento.totalizador_ids.tipo, "S-5001")

    # ── Conferência da competência ─────────────────────────────────────────

    def _conferencia_apurada(self):
        conferencia = self.env["l10n_br.esocial.conferencia"].obter_ou_criar(
            self.company, "2024-03"
        )
        conferencia.action_apurar()
        return conferencia

    def _linha(self, conferencia, indicador):
        return conferencia.linha_ids.filtered(
            lambda linha: linha.indicador == indicador
        )

    def test_conferencia_fecha_quando_folha_bate(self):
        self._criar_payslip()
        evento_remun = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        self._consumir(evento_remun, retorno_s5001(self.cpf_employee))
        evento_pgto = self._criar_evento("S-1210", state="sent", per_apur="2024-03")
        evento_pgto.registrar_aceite(
            nr_recibo=RECIBO_S1200, retorno_xml=retorno_s5012()
        )
        conferencia = self._conferencia_apurada()
        inss = self._linha(conferencia, "inss_segurado")
        self.assertAlmostEqual(inss.valor_folha, 330.0, places=2)
        self.assertAlmostEqual(inss.valor_totalizador, 330.0, places=2)
        self.assertFalse(inss.divergente)
        irrf = self._linha(conferencia, "irrf")
        self.assertAlmostEqual(irrf.valor_totalizador, 85.2, places=2)
        self.assertFalse(irrf.divergente)
        self.assertEqual(conferencia.divergencia_count, 0)
        self.assertEqual(conferencia.state, "ok")

    def test_conferencia_acusa_divergencia_de_inss(self):
        """Governo apurou INSS diferente do calculado: tem de aparecer."""
        self._criar_payslip()
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        self._consumir(evento, retorno_s5001(self.cpf_employee, inss=300.0))
        conferencia = self._conferencia_apurada()
        inss = self._linha(conferencia, "inss_segurado")
        self.assertTrue(inss.divergente)
        self.assertAlmostEqual(inss.diferenca, 30.0, places=2)
        self.assertEqual(conferencia.state, "divergente")

    def test_conferencia_sem_totalizador_e_divergencia(self):
        """Folha calculada sem retorno do governo é pendência, não zero."""
        self._criar_payslip()
        conferencia = self._conferencia_apurada()
        inss = self._linha(conferencia, "inss_segurado")
        self.assertTrue(inss.sem_totalizador)
        self.assertTrue(inss.divergente)

    def test_conferencia_tolera_centavos(self):
        self._criar_payslip()
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-03")
        self._consumir(evento, retorno_s5001(self.cpf_employee, inss=330.01))
        conferencia = self._conferencia_apurada()
        self.assertFalse(self._linha(conferencia, "inss_segurado").divergente)

    def test_indicadores_informativos_nunca_divergem(self):
        """Encargos patronais só existem do lado do governo (RF-31)."""
        self._criar_payslip()
        evento = self._criar_evento("S-1299", state="sent", per_apur="2024-03")
        evento.registrar_aceite(nr_recibo=RECIBO_S1299, retorno_xml=retorno_s5011())
        conferencia = self._conferencia_apurada()
        patronal = self._linha(conferencia, "cp_contribuinte")
        self.assertFalse(patronal.comparativo)
        self.assertFalse(patronal.divergente)
        self.assertAlmostEqual(patronal.valor_totalizador, 600.0, places=2)
        base = self._linha(conferencia, "base_cp")
        self.assertAlmostEqual(base.valor_totalizador, 3000.0, places=2)

    def test_conferencia_aponta_holerite_sem_evento(self):
        """Holerite confirmado fora do eSocial é a divergência mais comum."""
        self._criar_payslip()
        conferencia = self._conferencia_apurada()
        self.assertEqual(conferencia.payslip_sem_evento_count, 1)

    def test_holerite_com_s1200_aceito_sai_da_lista(self):
        payslip = self._criar_payslip()
        payslip.action_esocial_gerar_s1200()
        payslip.l10n_br_esocial_s1200_id.evento_id.write(
            {"state": "success", "nr_recibo": RECIBO_S1200}
        )
        conferencia = self._conferencia_apurada()
        self.assertEqual(conferencia.payslip_sem_evento_count, 0)

    def test_conferencia_ignora_outra_competencia(self):
        self._criar_payslip()
        evento = self._criar_evento("S-1200", state="sent", per_apur="2024-02")
        self._consumir(evento, retorno_s5001(self.cpf_employee, per_apur="2024-02"))
        conferencia = self._conferencia_apurada()
        self.assertTrue(self._linha(conferencia, "inss_segurado").sem_totalizador)

    def test_reapuracao_substitui_linhas(self):
        self._criar_payslip()
        conferencia = self._conferencia_apurada()
        quantidade = len(conferencia.linha_ids)
        conferencia.action_apurar()
        self.assertEqual(len(conferencia.linha_ids), quantidade)

    def test_obter_ou_criar_nao_duplica(self):
        modelo = self.env["l10n_br.esocial.conferencia"]
        primeira = modelo.obter_ou_criar(self.company, "2024-03")
        segunda = modelo.obter_ou_criar(self.company, "2024-03")
        self.assertEqual(primeira, segunda)
