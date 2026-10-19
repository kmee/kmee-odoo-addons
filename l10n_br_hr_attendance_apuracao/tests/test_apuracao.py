# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes da apuração no ORM (RP-09 a RP-15)."""

from datetime import date, datetime, timedelta

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestApuracao(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.rep = cls.env["l10n_br.hr.rep"].create(
            {
                "name": "REP da apuração",
                "tipo": "rep_c",
                "numero_fabricacao": "11111111111111111",
                "cnpj_cpf": "12345678000195",
                "atestado_date_start": "2020-01-01",
                "atestado_date_end": "2099-12-31",
            }
        )
        # Calendário 8h-12h / 13h-17h de segunda a sexta, no fuso de Brasília.
        cls.calendario = cls.env["resource.calendar"].create(
            {
                "name": "Jornada 44h - teste",
                "tz": "America/Sao_Paulo",
                "hours_per_day": 8.0,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "%s manhã" % dia,
                            "dayofweek": dia,
                            "hour_from": 8.0,
                            "hour_to": 12.0,
                        },
                    )
                    for dia in ("0", "1", "2", "3", "4")
                ]
                + [
                    (
                        0,
                        0,
                        {
                            "name": "%s tarde" % dia,
                            "dayofweek": dia,
                            "hour_from": 13.0,
                            "hour_to": 17.0,
                        },
                    )
                    for dia in ("0", "1", "2", "3", "4")
                ],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Ana Apuração",
                "tz": "America/Sao_Paulo",
                "resource_calendar_id": cls.calendario.id,
                "cnpj_cpf": "434.612.928-50",
            }
        )
        cls.contract = cls.env["hr.contract"].create(
            {
                "name": "Contrato Ana",
                "employee_id": cls.employee.id,
                "wage": 3000.0,
                "date_start": date(2026, 1, 1),
                "state": "open",
                "resource_calendar_id": cls.calendario.id,
                "company_id": cls.company.id,
            }
        )
        cls.nsr = 0

    @classmethod
    def _marcar(cls, dia, *horas_locais):
        """Grava marcações a partir de horários LOCAIS (Brasília, -3).

        A soma do fuso vai por ``timedelta``: somar 3 na hora estoura quando a
        marcação é noturna, e é justamente esse o caso interessante.
        """
        vals = []
        for hora, minuto in horas_locais:
            cls.nsr += 1
            vals.append(
                {
                    "nsr": cls.nsr,
                    "rep_id": cls.rep.id,
                    "company_id": cls.company.id,
                    "employee_id": cls.employee.id,
                    "datetime_marcacao": datetime(2026, 3, dia, hora, minuto)
                    + timedelta(hours=3),
                    "origem": "rep_c",
                }
            )
        return cls.env["l10n_br.hr.marcacao"]._criar_marcacoes(vals)

    def _apurar_dia(self, dia):
        periodo = self.env["l10n_br.hr.apuracao.periodo"].create(
            {
                "name": "Março/2026",
                "date_from": date(2026, 3, dia),
                "date_to": date(2026, 3, dia),
                "company_id": self.company.id,
                "employee_ids": [(6, 0, self.employee.ids)],
            }
        )
        periodo.action_apurar()
        return periodo, periodo.dia_ids.filtered(lambda d: d.date == date(2026, 3, dia))

    # ------------------------------------------------------------------

    def test_jornada_padrao_sem_extras(self):
        """Segunda-feira 8h-12h/13h-17h: bate exatamente o previsto."""
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        _periodo, apuracao = self._apurar_dia(2)
        self.assertEqual(apuracao.jornada_prevista, 8.0)
        self.assertEqual(apuracao.jornada_realizada, 8.0)
        self.assertEqual(apuracao.horas_extras, 0.0)
        self.assertEqual(apuracao.atraso, 0.0)
        self.assertTrue(apuracao.paridade_ok)
        self.assertFalse(apuracao.falta)

    def test_pares_viram_sessoes_de_attendance(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        _periodo, apuracao = self._apurar_dia(2)
        self.assertEqual(len(apuracao.attendance_ids), 2)
        self.assertEqual(
            sorted(apuracao.attendance_ids.mapped("l10n_br_seq_par")), [1, 2]
        )
        entrada = apuracao.marcacao_ids.filtered(lambda m: m.tipo_marcacao == "E")
        self.assertEqual(len(entrada), 2)

    def test_variacao_dentro_da_tolerancia_nao_gera_extra(self):
        self._marcar(3, (7, 57), (12, 0), (13, 0), (17, 4))
        _periodo, apuracao = self._apurar_dia(3)
        self.assertEqual(apuracao.horas_extras, 0.0)
        self.assertEqual(apuracao.atraso, 0.0)

    def test_meia_hora_extra_e_computada(self):
        self._marcar(4, (8, 0), (12, 0), (13, 0), (17, 30))
        _periodo, apuracao = self._apurar_dia(4)
        self.assertAlmostEqual(apuracao.horas_extras, 0.5, places=4)
        self.assertAlmostEqual(apuracao.he_50, 0.5, places=4)
        self.assertEqual(apuracao.he_100, 0.0)

    def test_atraso_acima_da_tolerancia(self):
        self._marcar(5, (8, 30), (12, 0), (13, 0), (17, 0))
        _periodo, apuracao = self._apurar_dia(5)
        self.assertAlmostEqual(apuracao.atraso, 0.5, places=4)
        self.assertEqual(apuracao.horas_extras, 0.0)

    def test_intervalo_suprimido_gera_verba(self):
        """Art. 71, § 4º: 30 minutos de intervalo em jornada de 8h."""
        self._marcar(6, (8, 0), (12, 0), (12, 30), (16, 30))
        _periodo, apuracao = self._apurar_dia(6)
        self.assertAlmostEqual(apuracao.intrajornada_gozada, 0.5, places=4)
        self.assertAlmostEqual(apuracao.intrajornada_devida, 1.0, places=4)
        self.assertAlmostEqual(apuracao.intrajornada_suprimida, 0.5, places=4)
        self.assertIn("Intervalo intrajornada suprimido", apuracao.inconsistencia)

    def test_marcacao_impar_bloqueia_paridade(self):
        self._marcar(9, (8, 0), (12, 0), (13, 0))
        _periodo, apuracao = self._apurar_dia(9)
        self.assertFalse(apuracao.paridade_ok)
        self.assertIn("sem par", apuracao.inconsistencia)

    def test_dia_util_sem_marcacao_e_falta_injustificada(self):
        _periodo, apuracao = self._apurar_dia(10)
        self.assertTrue(apuracao.falta)
        self.assertTrue(apuracao.falta_injustificada)

    def test_ocorrencia_que_abona_tira_a_injustificada(self):
        _periodo, apuracao = self._apurar_dia(11)
        self.assertTrue(apuracao.falta_injustificada)
        apuracao.write(
            {
                "ocorrencia_ids": [
                    (
                        6,
                        0,
                        [
                            self.env.ref(
                                "l10n_br_hr_attendance_apuracao.ocorrencia_atestado"
                            ).id
                        ],
                    )
                ]
            }
        )
        apuracao.apurar()
        self.assertTrue(apuracao.falta)
        self.assertFalse(apuracao.falta_injustificada)

    def test_domingo_sem_jornada_prevista_nao_e_falta(self):
        """1º de março de 2026 é domingo."""
        _periodo, apuracao = self._apurar_dia(1)
        self.assertEqual(apuracao.jornada_prevista, 0.0)
        self.assertFalse(apuracao.falta)

    def test_trabalho_em_domingo_vai_para_faixa_de_cem_por_cento(self):
        self._marcar(1, (8, 0), (12, 0))
        _periodo, apuracao = self._apurar_dia(1)
        self.assertAlmostEqual(apuracao.horas_extras, 4.0, places=4)
        self.assertAlmostEqual(apuracao.he_100, 4.0, places=4)
        self.assertEqual(apuracao.he_50, 0.0)

    def test_adicional_noturno_com_hora_reduzida(self):
        """21h as 23h: uma hora cronológica noturna vira 1,142857 computada."""
        self._marcar(2, (21, 0), (23, 0))
        _periodo, apuracao = self._apurar_dia(2)
        self.assertAlmostEqual(apuracao.noturno, 1.0, places=4)
        self.assertAlmostEqual(apuracao.noturno_computado, 8.0 / 7.0, places=4)

    def test_marcacao_desconsiderada_sai_do_calculo(self):
        marcacoes = self._marcar(12, (8, 0), (8, 1), (12, 0), (13, 0), (17, 0))
        duplicada = marcacoes.filtered(
            lambda m: m.datetime_marcacao == datetime(2026, 3, 12, 11, 1)
        )
        duplicada.action_desconsiderar("Batida em duplicidade no relógio")
        _periodo, apuracao = self._apurar_dia(12)
        self.assertTrue(apuracao.paridade_ok)
        self.assertEqual(apuracao.jornada_realizada, 8.0)
        # A marcação continua no dia, visível no espelho de ponto.
        self.assertIn(duplicada, apuracao.marcacao_ids)

    def test_interjornada_violada_vira_inconsistencia(self):
        self._marcar(2, (14, 0), (23, 0))
        self._marcar(3, (7, 0), (12, 0))
        periodo = self.env["l10n_br.hr.apuracao.periodo"].create(
            {
                "name": "Março/2026 - interjornada",
                "date_from": date(2026, 3, 2),
                "date_to": date(2026, 3, 3),
                "employee_ids": [(6, 0, self.employee.ids)],
            }
        )
        periodo.action_apurar()
        dia3 = periodo.dia_ids.filtered(lambda d: d.date == date(2026, 3, 3))
        self.assertFalse(dia3.interjornada_ok)
        self.assertIn("Interjornada", dia3.inconsistencia)

    def test_contrato_dispensado_nao_gera_apuracao(self):
        """Art. 62 da CLT: quem não tem controle de jornada não é apurado."""
        self.contract.write(
            {
                "l10n_br_dispensado_controle_jornada": True,
                "l10n_br_motivo_dispensa_jornada": "gestao",
            }
        )
        periodo = self.env["l10n_br.hr.apuracao.periodo"].create(
            {
                "name": "Março/2026 - dispensado",
                "date_from": date(2026, 3, 2),
                "date_to": date(2026, 3, 6),
                "employee_ids": [(6, 0, self.employee.ids)],
            }
        )
        periodo.action_apurar()
        self.assertFalse(periodo.dia_ids)

    # ------------------------------------------------------------------
    # Fechamento
    # ------------------------------------------------------------------

    def test_fechamento_trava_reapuracao(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo, apuracao = self._apurar_dia(2)
        periodo.action_fechar()
        self.assertEqual(periodo.state, "fechado")
        self.assertEqual(apuracao.state, "fechado")
        with self.assertRaises(UserError):
            apuracao.apurar()

    def test_reabrir_permite_reapurar(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo, apuracao = self._apurar_dia(2)
        periodo.action_fechar()
        periodo.action_reabrir()
        self.assertEqual(apuracao.state, "apurado")
        apuracao.apurar()

    def test_marcacao_impar_bloqueia_o_fechamento(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0))
        periodo, _apuracao = self._apurar_dia(2)
        with self.assertRaises(UserError):
            periodo.action_fechar()

    def test_marcacao_pendente_de_conciliacao_bloqueia_o_fechamento(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        self.env["l10n_br.hr.marcacao"]._criar_marcacoes(
            [
                {
                    "nsr": 9999,
                    "rep_id": self.rep.id,
                    "company_id": self.company.id,
                    "datetime_marcacao": datetime(2026, 3, 2, 11, 0),
                    "cpf": "11122233396",
                    "origem": "rep_c",
                }
            ]
        )
        periodo, _apuracao = self._apurar_dia(2)
        with self.assertRaises(UserError):
            periodo.action_fechar()

    def test_reapuracao_nao_duplica_sessoes(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        _periodo, apuracao = self._apurar_dia(2)
        apuracao.apurar()
        self.assertEqual(len(apuracao.attendance_ids), 2)
