# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: TRCT completo (RF-06) — verbas rescisórias por tipo de rescisão.

Cada teste confere o TRCT LINHA A LINHA: os valores esperados são
recalculados de forma INDEPENDENTE (funções puras de salary_rules_br +
tabelas fiscais vigentes lidas do banco), não apenas repetindo a fórmula da
regra XML. Isso valida que a regra usa a variável/condição corretas — não
só que a função pura está certa (essa é coberta em outro lugar).
"""
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

from odoo.addons.l10n_br_hr_payroll.models.salary_rules_br import (
    calc_aviso_previo_dias,
    calc_decimo_avos,
    calc_inss,
    calc_irrf_mais_favoravel,
    calc_media_habitual,
    calc_meses_trabalhados,
    dias_trabalhados_mes,
    round_money,
)

from .common import VacationCommon


@tagged("post_install", "-at_install")
class TestTRCTSemJustaCausa(VacationCommon):
    """TRCT conferido à mão: demissão sem justa causa, 2 anos de casa, HE habitual."""

    def setUp(self):
        super().setUp()
        self.wage = 3000.00
        self.date_start = date(2024, 1, 10)
        self.date_to = date(2026, 8, 20)
        self.emp = self._create_employee("TRCT Sem Justa Causa")
        self.contract = self._create_contract(
            self.emp, wage=self.wage, date_start=self.date_start
        )
        # Divisor da jornada do próprio ambiente (RF-26); lido em vez de
        # fixado, para não presumir 220 se o calendário padrão for outro.
        self.divisor = self.contract._l10n_br_divisor_horas_mensais()
        # 12 meses anteriores com hora extra 50% HABITUAL (8h/mês) — RF-18.
        self.valores_he = []
        for i in range(12, 0, -1):
            ref = self.date_to - relativedelta(months=i)
            mensal = self.env["hr.payslip"].create(
                {
                    "name": f"Mensal {ref.month}/{ref.year}",
                    "employee_id": self.emp.id,
                    "contract_id": self.contract.id,
                    "struct_id": self.structure_clt.id,
                    "date_from": ref.replace(day=1),
                    "date_to": ref.replace(day=1) + relativedelta(day=31),
                    "l10n_br_horas_extras_50": 8.0,
                    "company_id": self.env.company.id,
                }
            )
            mensal.action_payslip_done()
            self.valores_he.append(self._get_line_total(mensal, "HE_50"))
        self.media = calc_media_habitual(self.valores_he, 12)

        # 1º período aquisitivo, integralmente VENCIDO e nunca gozado; o
        # período concessivo (12 meses após o término) já expirou antes da
        # rescisão → paga em DOBRO (CLT art. 137).
        self.alloc_vencida = self.env["hr.leave.allocation"].create(
            {
                "employee_id": self.emp.id,
                "holiday_status_id": self.leave_type_ferias.id,
                "date_from": date(2024, 1, 10),
                "date_to": date(2025, 1, 9),
            }
        )
        self.alloc_vencida.action_validate()
        self.assertEqual(self.alloc_vencida.number_of_days, 30)

        self.rescisao = self.env["hr.payslip"].create(
            {
                "name": "Rescisão TRCT",
                "employee_id": self.emp.id,
                "contract_id": self.contract.id,
                "struct_id": self.structure_rescisao.id,
                "date_from": date(2026, 8, 1),
                "date_to": self.date_to,
                "l10n_br_tipo_rescisao": "sem_justa_causa",
                "l10n_br_aviso_previo": "indenizado",
                "company_id": self.env.company.id,
            }
        )
        self.rescisao.compute_sheet()
        self.g = lambda code: self._get_line_total(self.rescisao, code)

    def _tabela_inss(self):
        return self.env["l10n_br.hr.payroll.inss.faixa"]._tabela(self.date_to)

    def _tabela_irrf(self):
        return self.env["l10n_br.hr.payroll.irrf.faixa"]._tabela(self.date_to)

    def _tabela_redutor(self):
        return self.env["l10n_br.hr.payroll.irrf.redutor"]._tabela(self.date_to)

    def _desconto_simplificado(self):
        return self.env["l10n_br.hr.payroll.irrf.faixa"]._desconto_simplificado(
            self.date_to
        )

    def test_01_aviso_previo_36_dias(self):
        """Lei 12.506/2011: 30 dias + 3 por ano completo (2 anos) = 36 dias."""
        self.assertEqual(calc_aviso_previo_dias(self.date_start, self.date_to), 36)
        self.assertEqual(self.rescisao._l10n_br_dias_aviso_previo(), 36)

    def test_02_saldo_de_salario(self):
        """Saldo = dias de vigência no mês (1 a 20/08) × salário/30. Sem média."""
        dias = dias_trabalhados_mes(
            self.rescisao.date_from, self.rescisao.date_to, self.date_start, None
        )
        self.assertEqual(dias, 20)
        esperado = round_money(self.wage / 30 * dias)
        self.assertAlmostEqualMoney(self.g("SALDO_SALARIO"), esperado)

    def test_03_inss_e_irrf_do_saldo(self):
        saldo = self.g("SALDO_SALARIO")
        inss_esperado = calc_inss(saldo, self._tabela_inss())
        self.assertAlmostEqualMoney(self.g("INSS"), inss_esperado)
        base_irrf_esperada = saldo - inss_esperado
        self.assertAlmostEqualMoney(self.g("BASE_IRRF"), base_irrf_esperada)
        irrf_esperado = calc_irrf_mais_favoravel(
            saldo,
            base_irrf_esperada,
            self._tabela_irrf(),
            self._desconto_simplificado(),
            self._tabela_redutor(),
        )
        self.assertAlmostEqualMoney(self.g("IRRF"), irrf_esperado)

    def test_04_decimo_proporcional_com_projecao_e_media(self):
        """Aviso indenizado projeta a referência (Súmula 371 TST): mais avos
        do que sem projeção."""
        referencia_projetada = self.date_to + relativedelta(days=36)
        avos_esperado = calc_decimo_avos(self.date_start, referencia_projetada)
        avos_sem_projecao = calc_decimo_avos(self.date_start, self.date_to)
        self.assertEqual(self.rescisao.l10n_br_avos_13, avos_esperado)
        self.assertGreater(avos_esperado, avos_sem_projecao)

        base_com_media = self.wage + self.media
        decimo_esperado = round_money(base_com_media * avos_esperado / 12)
        self.assertAlmostEqualMoney(self.g("DECIMO_RESCISAO"), decimo_esperado)

    def test_05_ferias_proporcionais_indenizadas(self):
        """Férias proporcionais (avos do período em curso, já projetado)."""
        avos = self.rescisao.l10n_br_avos_ferias
        self.assertGreater(avos, 0)
        base_com_media = self.wage + self.media
        esperado = round_money(base_com_media * avos / 12)
        self.assertAlmostEqualMoney(self.g("FERIAS_INDENIZADAS"), esperado)
        self.assertAlmostEqualMoney(
            self.g("ADICIONAL_FERIAS_INDENIZADAS"), round_money(esperado / 3)
        )
        # Indenizatórias: fora das bases de INSS/FGTS (só saldo e 13º sofrem).
        inss = self.g("INSS")
        inss_13 = self.g("INSS_13")
        saldo = self.g("SALDO_SALARIO")
        decimo = self.g("DECIMO_RESCISAO")
        self.assertAlmostEqualMoney(inss, calc_inss(saldo, self._tabela_inss()))
        self.assertAlmostEqualMoney(inss_13, calc_inss(decimo, self._tabela_inss()))

    def test_06_ferias_vencidas_em_dobro(self):
        """Período vencido (30 dias, nunca gozado) pago em DOBRO: o período
        concessivo (até 09/01/2026) expirou antes da rescisão (20/08/2026)."""
        dados = self.rescisao._l10n_br_ferias_vencidas_dados()
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["dias"], 30)
        self.assertTrue(dados[0]["dobro"])

        base_com_media = self.wage + self.media
        esperado = round_money(base_com_media / 30 * 30 * 2)
        self.assertAlmostEqualMoney(self.g("FERIAS_VENCIDAS"), esperado)
        self.assertAlmostEqualMoney(
            self.g("ADICIONAL_FERIAS_VENCIDAS"), round_money(esperado / 3)
        )

    def test_07_aviso_previo_indenizado_e_fgts(self):
        """Aviso integral (sem justa causa): sem redução. FGTS incide 8%."""
        base_com_media = self.wage + self.media
        esperado = round_money(base_com_media / 30 * 36 * 1.0)
        self.assertAlmostEqualMoney(self.g("AVISO_PREVIO_INDENIZADO"), esperado)
        self.assertAlmostEqualMoney(self.g("FGTS_AVISO"), round_money(esperado * 0.08))

    def test_08_multa_40_por_cento_fgts_fallback(self):
        """Sem saldo informado: fallback 8% × salário × meses trabalhados."""
        meses = calc_meses_trabalhados(self.date_start, self.date_to)
        base_esperada = round_money(self.wage * 0.08 * meses)
        multa_esperada = round_money(base_esperada * 0.40)
        self.assertAlmostEqualMoney(self.g("MULTA_FGTS"), multa_esperada)

    def test_09_multa_usa_saldo_informado_quando_preenchido(self):
        """Com saldo real informado, o fallback não é usado."""
        self.rescisao.l10n_br_fgts_saldo_conta = 10000.00
        self.rescisao.compute_sheet()
        self.assertAlmostEqualMoney(
            self._get_line_total(self.rescisao, "MULTA_FGTS"), 4000.00
        )

    def test_10_net_soma_todas_as_verbas(self):
        g = self.g
        esperado = (
            g("SALDO_SALARIO")
            + g("DECIMO_RESCISAO")
            + g("FERIAS_INDENIZADAS")
            + g("ADICIONAL_FERIAS_INDENIZADAS")
            + g("FERIAS_VENCIDAS")
            + g("ADICIONAL_FERIAS_VENCIDAS")
            + g("AVISO_PREVIO_INDENIZADO")
            + g("MULTA_FGTS")
            - g("INSS")
            - g("INSS_13")
            - g("IRRF")
            - g("IRRF_13")
        )
        self.assertAlmostEqualMoney(g("NET"), esperado)
        self.assertGreater(g("NET"), 0.0)


@tagged("post_install", "-at_install")
class TestTiposDeRescisao(VacationCommon):
    """Verbas variam pelo tipo de rescisão (RF-06)."""

    def _rescisao(
        self, tipo, aviso=None, date_start=None, date_to=None, fgts_saldo=0.0
    ):
        emp = self._create_employee(f"Rescisão {tipo}")
        contract = self._create_contract(
            emp, wage=3000.00, date_start=date_start or date(2023, 1, 1)
        )
        vals = {
            "name": f"Rescisão {tipo}",
            "employee_id": emp.id,
            "contract_id": contract.id,
            "struct_id": self.structure_rescisao.id,
            "date_from": (date_to or date(2025, 6, 30)).replace(day=1),
            "date_to": date_to or date(2025, 6, 30),
            "l10n_br_tipo_rescisao": tipo,
            "l10n_br_fgts_saldo_conta": fgts_saldo,
            "company_id": self.env.company.id,
        }
        if aviso:
            vals["l10n_br_aviso_previo"] = aviso
        payslip = self.env["hr.payslip"].create(vals)
        payslip.compute_sheet()
        return payslip

    def test_sem_justa_causa_aviso_e_multa_integrais(self):
        payslip = self._rescisao("sem_justa_causa", aviso="indenizado")
        self.assertGreater(self._get_line_total(payslip, "AVISO_PREVIO_INDENIZADO"), 0)
        self.assertGreater(self._get_line_total(payslip, "MULTA_FGTS"), 0)
        self.assertGreater(self._get_line_total(payslip, "DECIMO_RESCISAO"), 0)
        self.assertGreater(self._get_line_total(payslip, "FERIAS_INDENIZADAS"), 0)

    def test_acordo_aviso_e_multa_pela_metade_e_um_quinto(self):
        """CLT art. 484-A, I: aviso 50% e multa 20% (não 40%)."""
        sem_justa = self._rescisao(
            "sem_justa_causa", aviso="indenizado", fgts_saldo=10000.00
        )
        acordo = self._rescisao("acordo", aviso="indenizado", fgts_saldo=10000.00)
        self.assertAlmostEqualMoney(
            self._get_line_total(acordo, "AVISO_PREVIO_INDENIZADO"),
            self._get_line_total(sem_justa, "AVISO_PREVIO_INDENIZADO") / 2,
        )
        self.assertAlmostEqualMoney(
            self._get_line_total(acordo, "MULTA_FGTS"), 10000.00 * 0.20
        )
        # 13º e férias proporcionais NÃO são reduzidos no acordo (CLT
        # art. 484-A, II: demais verbas na integralidade).
        self.assertAlmostEqualMoney(
            self._get_line_total(acordo, "DECIMO_RESCISAO"),
            self._get_line_total(sem_justa, "DECIMO_RESCISAO"),
        )

    def test_pedido_demissao_sem_aviso_indenizado_nem_multa(self):
        """Súmula 157 TST: 13º devido; mas sem aviso indenizado nem multa."""
        payslip = self._rescisao("pedido_demissao", aviso="nao_aplicavel")
        self.assertEqual(self._get_line_total(payslip, "AVISO_PREVIO_INDENIZADO"), 0.0)
        self.assertEqual(self._get_line_total(payslip, "MULTA_FGTS"), 0.0)
        self.assertGreater(self._get_line_total(payslip, "DECIMO_RESCISAO"), 0.0)
        self.assertGreater(self._get_line_total(payslip, "FERIAS_INDENIZADAS"), 0.0)

    def test_justa_causa_sem_decimo_sem_ferias_proporcionais(self):
        """Lei 4.090/62 art. 3º + Súmula 171 TST: nem 13º, nem proporcionais."""
        payslip = self._rescisao("justa_causa", aviso="nao_aplicavel")
        self.assertEqual(self._get_line_total(payslip, "DECIMO_RESCISAO"), 0.0)
        self.assertEqual(self._get_line_total(payslip, "FERIAS_INDENIZADAS"), 0.0)
        self.assertEqual(
            self._get_line_total(payslip, "ADICIONAL_FERIAS_INDENIZADAS"), 0.0
        )
        self.assertEqual(self._get_line_total(payslip, "AVISO_PREVIO_INDENIZADO"), 0.0)
        self.assertEqual(self._get_line_total(payslip, "MULTA_FGTS"), 0.0)
        # Saldo de salário continua devido, sempre.
        self.assertGreater(self._get_line_total(payslip, "SALDO_SALARIO"), 0.0)

    def test_justa_causa_ferias_vencidas_continuam_devidas(self):
        """CLT art. 146, caput: vencidas são devidas "qualquer que seja a
        causa" — inclusive na justa causa."""
        emp = self._create_employee("Justa Causa Vencidas")
        contract = self._create_contract(emp, wage=3000.00, date_start=date(2023, 1, 1))
        alloc = self.env["hr.leave.allocation"].create(
            {
                "employee_id": emp.id,
                "holiday_status_id": self.leave_type_ferias.id,
                "date_from": date(2023, 1, 1),
                "date_to": date(2023, 12, 31),
            }
        )
        alloc.action_validate()
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Rescisão Justa Causa Vencidas",
                "employee_id": emp.id,
                "contract_id": contract.id,
                "struct_id": self.structure_rescisao.id,
                "date_from": date(2025, 6, 1),
                "date_to": date(2025, 6, 30),
                "l10n_br_tipo_rescisao": "justa_causa",
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        self.assertGreater(self._get_line_total(payslip, "FERIAS_VENCIDAS"), 0.0)
        self.assertEqual(self._get_line_total(payslip, "DECIMO_RESCISAO"), 0.0)
