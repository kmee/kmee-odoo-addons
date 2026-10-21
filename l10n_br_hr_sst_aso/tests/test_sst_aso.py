# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.l10n_br_hr_sst.tests.common import SstCommon

from ..models.hr_employee_medical_examination import (
    TIPO_ASO_ADMISSIONAL,
    TIPO_ASO_DEMISSIONAL,
    TIPO_ASO_PERIODICO,
)


@tagged("post_install", "-at_install")
class TestSstAso(SstCommon):
    """RS-09 a RS-11 e RS-20: ASO, PCMSO, bloqueios e sigilo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.exame_model = cls.env["hr.employee.medical.examination"]
        cls.hoje = fields.Date.context_today(cls.exame_model)
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
                "date_from": cls.hoje - relativedelta(months=1),
                "periodicidade_meses": 12,
                "state": "vigente",
            }
        )
        cls.procedimento = cls.env["l10n_br.esocial.procedimento.diagnostico"].search(
            [], limit=1
        )
        cls.employee.birthday = cls.hoje - relativedelta(years=50)

    def _cria_exame(self, tipo=TIPO_ASO_ADMISSIONAL, date=None):
        return self.exame_model.l10n_br_gerar_aso(
            self.employee, tipo, date=date or self.hoje
        )

    def _conclui(self, exame):
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

    # ── PCMSO ───────────────────────────────────────────────────────────────

    def test_pcmso_vigencia_invertida(self):
        with self.assertRaises(ValidationError):
            self.pcmso.write({"date_to": self.hoje - relativedelta(years=2)})

    def test_pcmso_periodicidade_positiva(self):
        with self.assertRaises(ValidationError):
            self.pcmso.write({"periodicidade_meses": 0})

    def test_pcmso_buscar_vigente(self):
        encontrado = self.env["l10n_br.sst.pcmso"].buscar_vigente(
            self.env.company, self.hoje
        )
        self.assertEqual(encontrado, self.pcmso)

    def test_pcmso_faixa_por_idade(self):
        self.env["l10n_br.sst.pcmso.faixa"].create(
            {
                "pcmso_id": self.pcmso.id,
                "name": "Acima de 45 anos",
                "idade_de": 45,
                "meses": 6,
            }
        )
        self.assertEqual(
            self.pcmso.periodicidade_do_empregado(self.employee, self.hoje), 6
        )

    def test_pcmso_faixa_exige_exposicao(self):
        """Faixa de exposto não vale para quem não tem risco vigente."""
        self.env["l10n_br.sst.pcmso.faixa"].create(
            {
                "pcmso_id": self.pcmso.id,
                "name": "Expostos",
                "exige_exposicao": True,
                "meses": 6,
            }
        )
        self.contract.l10n_br_sst_ambiente_id = False
        self.assertEqual(
            self.pcmso.periodicidade_do_empregado(self.employee, self.hoje), 12
        )

    # ── ASO ─────────────────────────────────────────────────────────────────

    def test_gerar_aso_vincula_pcmso(self):
        exame = self._cria_exame()
        self.assertEqual(exame.l10n_br_pcmso_id, self.pcmso)
        self.assertEqual(exame.l10n_br_tipo_aso_codigo, TIPO_ASO_ADMISSIONAL)

    def test_concluir_sem_dados_obrigatorios(self):
        exame = self._cria_exame()
        with self.assertRaises(UserError):
            exame.to_done()

    def test_concluir_calcula_vencimento(self):
        exame = self._conclui(self._cria_exame())
        self.assertEqual(exame.state, "done")
        self.assertEqual(
            exame.l10n_br_date_vencimento, self.hoje + relativedelta(months=12)
        )

    def test_demissional_nao_gera_vencimento(self):
        exame = self._conclui(self._cria_exame(tipo=TIPO_ASO_DEMISSIONAL))
        self.assertFalse(exame.l10n_br_date_vencimento)

    def test_resultado_sincroniza_com_o_campo_da_oca(self):
        exame = self._cria_exame()
        exame.l10n_br_resultado = "2"
        exame._onchange_l10n_br_resultado()
        self.assertEqual(exame.result, "failed")

    def test_inapto_nao_e_apto_com_restricao(self):
        exame = self._cria_exame()
        with self.assertRaises(ValidationError):
            exame.write({"l10n_br_resultado": "2", "l10n_br_com_restricao": True})

    def test_exame_complementar_para_o_evento(self):
        exame = self._cria_exame()
        linha = self.env["l10n_br.sst.exame.complementar"].create(
            {
                "examination_id": exame.id,
                "procedimento_id": self.procedimento.id,
                "date": self.hoje,
                "ord_exame": "1",
                "ind_result": "1",
            }
        )
        dados = linha._to_exame()
        self.assertEqual(dados["proc_realizado"], self.procedimento.codigo)
        self.assertEqual(dados["ord_exame"], 1)
        self.assertEqual(dados["ind_result"], 1)

    # ── Situação do trabalhador ─────────────────────────────────────────────

    def test_situacao_sem_aso(self):
        self.assertEqual(self.employee.l10n_br_sst_aso_situacao, "sem_aso")

    def test_situacao_em_dia(self):
        self._conclui(self._cria_exame())
        self.assertEqual(self.employee.l10n_br_sst_aso_situacao, "em_dia")

    def test_situacao_vencido(self):
        exame = self._conclui(
            self._cria_exame(date=self.hoje - relativedelta(months=18))
        )
        self.assertEqual(
            exame.l10n_br_date_vencimento, self.hoje - relativedelta(months=6)
        )
        self.assertEqual(self.employee.l10n_br_sst_aso_situacao, "vencido")

    def test_idade_do_empregado(self):
        self.assertEqual(self.employee._l10n_br_sst_idade(self.hoje), 50)

    def test_aso_de_retorno_so_acima_de_trinta_dias(self):
        self.assertFalse(self.employee.l10n_br_sst_gerar_aso_retorno(10))
        exame = self.employee.l10n_br_sst_gerar_aso_retorno(45, self.hoje)
        self.assertEqual(exame.l10n_br_tipo_aso_codigo, "2")

    # ── Bloqueios (RS-11) ───────────────────────────────────────────────────

    def test_admissao_sem_aso_bloqueia(self):
        self.env.company.l10n_br_sst_aso_politica = "bloqueia"
        employee = self.env["hr.employee"].create({"name": "Novo Trabalhador"})
        with self.assertRaises(UserError):
            self.env["hr.contract"].create(
                {
                    "name": "Contrato sem ASO",
                    "employee_id": employee.id,
                    "wage": 2000.0,
                    "date_start": self.hoje,
                    "state": "open",
                }
            )

    def test_admissao_sem_aso_apenas_alerta(self):
        self.env.company.l10n_br_sst_aso_politica = "alerta"
        employee = self.env["hr.employee"].create({"name": "Trabalhador Alertado"})
        contrato = self.env["hr.contract"].create(
            {
                "name": "Contrato alertado",
                "employee_id": employee.id,
                "wage": 2000.0,
                "date_start": self.hoje,
                "state": "open",
            }
        )
        self.assertTrue(contrato.message_ids)

    def test_admissao_com_aso_passa(self):
        self.env.company.l10n_br_sst_aso_politica = "bloqueia"
        self._conclui(self._cria_exame())
        self.contract.state = "draft"
        self.contract.state = "open"
        self.assertEqual(self.contract.state, "open")

    # ── Demissional (NR-7, item 7.5.11) ─────────────────────────────────────

    def _encerra(self, termino=None):
        """Encerra o contrato na data informada, sem esperar o cron do core."""
        self.contract.write({"date_end": termino or self.hoje, "state": "close"})
        return self.contract

    def _atividades_demissional(self):
        tipo = self.env.ref("l10n_br_hr_sst_aso.mail_activity_type_aso_demissional")
        return self.contract.activity_ids.filtered(lambda a: a.activity_type_id == tipo)

    def test_rescisao_sem_demissional_nao_bloqueia(self):
        """O demissional tem prazo de 10 dias após o término: não trava a rescisão.

        O bloqueio da política só vale para o admissional, que a NR-7 exige
        antes de o empregado assumir as atividades.
        """
        self.env.company.l10n_br_sst_aso_politica = "bloqueia"
        self._encerra()
        self.assertEqual(self.contract.state, "close")

    def test_dispensa_grau_1_e_2_ate_135_dias(self):
        self.env.company.l10n_br_sst_grau_risco = "2"
        self._conclui(self._cria_exame(date=self.hoje - relativedelta(days=100)))
        self._encerra()
        self.exame_model.cron_cobrar_demissional()
        self.assertEqual(self.contract.l10n_br_sst_demissional, "dispensado")
        self.assertFalse(self._atividades_demissional())

    def test_grau_3_e_4_dispensa_so_ate_90_dias(self):
        self.env.company.l10n_br_sst_grau_risco = "3"
        self._conclui(self._cria_exame(date=self.hoje - relativedelta(days=100)))
        self._encerra()
        self.exame_model.cron_cobrar_demissional()
        self.assertEqual(self.contract.l10n_br_sst_demissional, "cobrado")
        atividade = self._atividades_demissional()
        self.assertEqual(len(atividade), 1)
        self.assertEqual(atividade.date_deadline, self.hoje + relativedelta(days=10))

    def test_grau_3_dispensa_abaixo_de_90_dias(self):
        self.env.company.l10n_br_sst_grau_risco = "4"
        self._conclui(self._cria_exame(date=self.hoje - relativedelta(days=89)))
        self._encerra()
        self.exame_model.cron_cobrar_demissional()
        self.assertEqual(self.contract.l10n_br_sst_demissional, "dispensado")

    def test_sem_grau_de_risco_usa_o_prazo_menor(self):
        """Sem grau informado, vale o prazo mais restritivo (90 dias)."""
        self.env.company.l10n_br_sst_grau_risco = False
        self._conclui(self._cria_exame(date=self.hoje - relativedelta(days=100)))
        self._encerra()
        self.exame_model.cron_cobrar_demissional()
        self.assertEqual(self.contract.l10n_br_sst_demissional, "cobrado")

    def test_sem_exame_anterior_cobra(self):
        self.env.company.l10n_br_sst_grau_risco = "1"
        self._encerra()
        self.exame_model.cron_cobrar_demissional()
        self.assertEqual(self.contract.l10n_br_sst_demissional, "cobrado")

    def test_cobranca_nao_duplica(self):
        self.env.company.l10n_br_sst_grau_risco = "3"
        self._encerra()
        self.exame_model.cron_cobrar_demissional()
        self.exame_model.cron_cobrar_demissional()
        self.assertEqual(len(self._atividades_demissional()), 1)

    def test_demissional_concluido_fecha_a_cobranca(self):
        self.env.company.l10n_br_sst_grau_risco = "3"
        self._encerra()
        self.exame_model.cron_cobrar_demissional()
        self._conclui(self._cria_exame(tipo=TIPO_ASO_DEMISSIONAL))
        self.assertEqual(self.contract.l10n_br_sst_demissional, "realizado")
        self.assertFalse(self._atividades_demissional())

    def test_politica_ignora_nao_cobra(self):
        self.env.company.l10n_br_sst_aso_politica = "ignora"
        self._encerra()
        self.exame_model.cron_cobrar_demissional()
        self.assertFalse(self.contract.l10n_br_sst_demissional)
        self.assertFalse(self._atividades_demissional())

    # ── Agendamento automático (RS-10) ──────────────────────────────────────

    def test_cron_agenda_periodico(self):
        self._conclui(self._cria_exame(date=self.hoje - relativedelta(months=12)))
        criados = self.exame_model.cron_agendar_periodicos()
        self.assertTrue(criados)
        self.assertEqual(criados.l10n_br_tipo_aso_codigo, TIPO_ASO_PERIODICO)

    def test_cron_nao_duplica_pendente(self):
        self._conclui(self._cria_exame(date=self.hoje - relativedelta(months=12)))
        self.exame_model.cron_agendar_periodicos()
        segundos = self.exame_model.cron_agendar_periodicos()
        self.assertFalse(segundos)

    # ── Sigilo (RS-20) ──────────────────────────────────────────────────────

    def test_rh_nao_le_observacao_clinica(self):
        """Usuário de RH não enxerga o campo clínico (LGPD art. 11)."""
        exame = self._cria_exame()
        usuario_rh = self.env["res.users"].create(
            {
                "name": "Analista de RH",
                "login": "rh_sst_teste",
                "groups_id": [(6, 0, [self.env.ref("hr.group_hr_manager").id])],
            }
        )
        exame_rh = exame.with_user(usuario_rh)
        self.assertNotIn(
            "l10n_br_observacao_clinica",
            exame_rh.fields_get(),
        )
        with self.assertRaises(AccessError):
            exame_rh.read(["l10n_br_observacao_clinica"])

    def test_saude_ocupacional_le_observacao_clinica(self):
        exame = self._cria_exame()
        usuario_medico = self.env["res.users"].create(
            {
                "name": "Médica do Trabalho",
                "login": "medico_sst_teste",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("hr.group_hr_user").id,
                            self.env.ref("l10n_br_hr_sst_aso.group_sst_medico").id,
                        ],
                    )
                ],
            }
        )
        exame_medico = exame.with_user(usuario_medico)
        exame_medico.write({"l10n_br_observacao_clinica": "Audiometria alterada."})
        self.assertEqual(
            exame_medico.l10n_br_observacao_clinica, "Audiometria alterada."
        )

    def test_rh_nao_le_observacao_livre_do_exame(self):
        """A observação da OCA (note) pode ter dado clínico: sai do alcance do RH."""
        exame = self._cria_exame()
        exame.sudo().note = "Queixa de zumbido."
        usuario_rh = self._cria_usuario("rh_note", "hr.group_hr_manager")
        with self.assertRaises(AccessError):
            exame.with_user(usuario_rh).read(["note"])

    def test_exame_complementar_so_do_proprio_trabalhador(self):
        """Qualquer funcionário lia o exame complementar de todos os colegas."""
        exame = self._cria_exame()
        linha = self.env["l10n_br.sst.exame.complementar"].create(
            {
                "examination_id": exame.id,
                "procedimento_id": self.procedimento.id,
                "ind_result": "2",
            }
        )
        colega = self._cria_usuario("colega_sst")
        dono = self._cria_usuario("dono_sst")
        self.employee.user_id = dono
        linhas = self.env["l10n_br.sst.exame.complementar"]
        self.assertFalse(linhas.with_user(colega).search([("id", "=", linha.id)]))
        self.assertTrue(linhas.with_user(dono).search([("id", "=", linha.id)]))
        gestor_rh = self._cria_usuario("gestor_rh_sst", "hr.group_hr_manager")
        self.assertTrue(linhas.with_user(gestor_rh).search([("id", "=", linha.id)]))

    def test_saude_ocupacional_conclui_exame_com_seu_proprio_usuario(self):
        """O grupo precisa enxergar PCMSO e risco para calcular o vencimento."""
        exame = self._cria_exame()
        exame.write(
            {
                "l10n_br_resultado": "1",
                "l10n_br_medico_nome": "Dr. Examinador",
            }
        )
        medico = self._cria_usuario(
            "medico_conclui_sst", "l10n_br_hr_sst_aso.group_sst_medico"
        )
        exame.with_user(medico).to_done()
        self.assertEqual(exame.state, "done")
        self.assertTrue(exame.l10n_br_date_vencimento)
        self.assertEqual(exame.result, "passed")

    def test_contrato_checa_aso_mesmo_sem_ler_exame_de_terceiros(self):
        """Quem abre o contrato não lê o exame do colega, mas o ASO existe."""
        self.env.company.l10n_br_sst_aso_politica = "bloqueia"
        self._conclui(self._cria_exame())
        gestor = self._cria_usuario(
            "gestor_contrato_sst", "hr_contract.group_hr_contract_manager"
        )
        contrato = self.contract.with_user(gestor)
        self.assertTrue(contrato._l10n_br_sst_exige_aso(TIPO_ASO_ADMISSIONAL))

    def test_cron_ignora_exame_superado_por_outro(self):
        """ASO antigo, já superado por um recente, não gera periódico novo."""
        self._conclui(self._cria_exame(date=self.hoje - relativedelta(months=24)))
        self._conclui(self._cria_exame(tipo=TIPO_ASO_PERIODICO))
        self.assertFalse(self.exame_model.cron_agendar_periodicos())

    def _cria_usuario(self, login, *grupos):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "groups_id": [
                    (6, 0, [self.env.ref(g).id for g in ("base.group_user", *grupos)])
                ],
            }
        )
