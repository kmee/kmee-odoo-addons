# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Testes da ponte ponto -> folha (RP-16 a RP-19)."""

from datetime import date, datetime, timedelta

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPonteFolha(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.rep = cls.env["l10n_br.hr.rep"].create(
            {
                "name": "REP da folha",
                "tipo": "rep_c",
                "numero_fabricacao": "22222222222222222",
                "cnpj_cpf": "12345678000195",
                "atestado_date_start": "2020-01-01",
                "atestado_date_end": "2099-12-31",
            }
        )
        cls.calendario = cls.env["resource.calendar"].create(
            {
                "name": "Jornada 44h - folha",
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
                "name": "Carlos Folha",
                "tz": "America/Sao_Paulo",
                "resource_calendar_id": cls.calendario.id,
                "l10n_br_tipo_contrato": "clt",
            }
        )
        cls.contract = cls.env["hr.contract"].create(
            {
                "name": "Contrato Carlos",
                "employee_id": cls.employee.id,
                "wage": 4400.0,
                "date_start": date(2026, 1, 1),
                "state": "open",
                "resource_calendar_id": cls.calendario.id,
                "struct_id": cls.env.ref("l10n_br_hr_payroll.structure_clt").id,
                "company_id": cls.company.id,
            }
        )
        cls.nsr = 0

    @classmethod
    def _marcar(cls, dia, *horas_locais):
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

    def _apurar_marco(self, fechar=True):
        periodo = self.env["l10n_br.hr.apuracao.periodo"].create(
            {
                "name": "Março/2026",
                "date_from": date(2026, 3, 1),
                "date_to": date(2026, 3, 31),
                "company_id": self.company.id,
                "employee_ids": [(6, 0, self.employee.ids)],
            }
        )
        periodo.action_apurar()
        if fechar:
            periodo.with_context(l10n_br_forcar_fechamento=True).action_fechar()
        return periodo

    def _holerite(self):
        holerite = self.env["hr.payslip"].create(
            {
                "name": "Holerite Carlos 03/2026",
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "struct_id": self.contract.struct_id.id,
                "date_from": date(2026, 3, 1),
                "date_to": date(2026, 3, 31),
                "company_id": self.company.id,
            }
        )
        holerite.compute_sheet()
        return holerite

    def _valor(self, holerite, codigo):
        linha = holerite.line_ids.filtered(lambda linha: linha.code == codigo)
        return sum(linha.mapped("total"))

    # ------------------------------------------------------------------

    def test_sem_apuracao_o_comportamento_antigo_e_preservado(self):
        """Quem ainda não usa ponto eletrônico não pode ter a folha quebrada."""
        holerite = self._holerite()
        self.assertFalse(holerite.l10n_br_tem_apuracao)
        self.assertTrue(holerite.worked_days_line_ids)
        self.assertIn("WORK100", holerite.worked_days_line_ids.mapped("code"))

    def test_horas_extras_vem_da_apuracao_sem_digitacao(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (19, 0))
        self._apurar_marco()
        holerite = self._holerite()
        self.assertTrue(holerite.l10n_br_tem_apuracao)
        self.assertAlmostEqual(holerite.l10n_br_horas_extras_50, 2.0, places=2)
        self.assertGreater(self._valor(holerite, "HE_50"), 0.0)

    def test_horas_noturnas_vem_da_apuracao(self):
        self._marcar(2, (22, 0), (23, 0))
        self._apurar_marco()
        holerite = self._holerite()
        self.assertAlmostEqual(holerite.l10n_br_horas_noturnas, 1.0, places=2)
        self.assertGreater(self._valor(holerite, "ADICIONAL_NOTURNO"), 0.0)

    def test_faltas_vem_da_apuracao(self):
        """Março de 2026 tem 22 dias úteis; sem marcação, todos são falta."""
        self._apurar_marco()
        holerite = self._holerite()
        self.assertEqual(holerite.l10n_br_faltas_injustificadas, 22)
        self.assertGreater(self._valor(holerite, "FALTAS"), 0.0)

    def test_worked_days_derivado_da_presenca_efetiva(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        self._marcar(3, (8, 0), (12, 0), (13, 0), (17, 0))
        self._apurar_marco()
        holerite = self._holerite()
        work100 = holerite.worked_days_line_ids.filtered(
            lambda linha: linha.code == "WORK100"
        )
        self.assertEqual(work100.number_of_days, 2)
        self.assertAlmostEqual(work100.number_of_hours, 16.0, places=2)
        faltas = holerite.worked_days_line_ids.filtered(
            lambda linha: linha.code == "FALTAS"
        )
        self.assertEqual(faltas.number_of_days, 20)

    def test_ausencia_abonada_nao_entra_como_falta(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (17, 0))
        periodo = self._apurar_marco(fechar=False)
        atestado = self.env.ref("l10n_br_hr_attendance_apuracao.ocorrencia_atestado")
        dia3 = periodo.dia_ids.filtered(lambda dia: dia.date == date(2026, 3, 3))
        dia3.write({"ocorrencia_ids": [(6, 0, atestado.ids)]})
        dia3.apurar()
        holerite = self._holerite()
        abonadas = holerite.worked_days_line_ids.filtered(
            lambda linha: linha.code == "AUSENCIA_ABONADA"
        )
        self.assertEqual(abonadas.number_of_days, 1)
        self.assertEqual(holerite.l10n_br_faltas_injustificadas, 20)

    def test_intervalo_suprimido_gera_rubrica_indenizatoria(self):
        """Art. 71, § 4º: entra no líquido, fora da base de INSS e IRRF."""
        self._marcar(2, (8, 0), (12, 0), (12, 30), (16, 30))
        self._apurar_marco()
        holerite = self._holerite()
        self.assertAlmostEqual(holerite.l10n_br_intervalo_suprimido, 0.5, places=2)
        valor = self._valor(holerite, "INTERV_SUPRIMIDO")
        self.assertGreater(valor, 0.0)
        categoria = holerite.line_ids.filtered(
            lambda linha: linha.code == "INTERV_SUPRIMIDO"
        ).category_id
        self.assertEqual(categoria.code, "IND")

        # O bruto (base de INSS e IRRF) é só BASIC + ALW: a verba
        # indenizatória fica de fora.
        no_bruto = holerite.line_ids.filtered(
            lambda linha: linha.category_id.code in ("BASIC", "ALW")
        )
        self.assertNotIn("INTERV_SUPRIMIDO", no_bruto.mapped("code"))
        self.assertAlmostEqual(
            self._valor(holerite, "GROSS"), sum(no_bruto.mapped("total")), places=2
        )

        # E o líquido a contém: é verba paga, não apenas informativa.
        descontos = sum(
            holerite.line_ids.filtered(
                lambda linha: linha.category_id.code == "DED"
            ).mapped("total")
        )
        self.assertAlmostEqual(
            self._valor(holerite, "NET"),
            self._valor(holerite, "GROSS") + valor - descontos,
            places=2,
        )

    def test_dsr_sobre_horas_extras(self):
        """Súmula 172 do TST: HE refletem no repouso."""
        self._marcar(2, (8, 0), (12, 0), (13, 0), (19, 0))
        self._apurar_marco()
        holerite = self._holerite()
        self.assertGreater(self._valor(holerite, "DSR_HE"), 0.0)

    def test_totais_publicados_no_localdict(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (19, 0))
        self._apurar_marco()
        holerite = self._holerite()
        tools = holerite._get_tools_dict()
        self.assertIn("ponto", tools)
        self.assertAlmostEqual(tools["ponto"].he_50, 2.0, places=2)
        self.assertGreater(tools["ponto"].dias_uteis, 0)

    # ------------------------------------------------------------------
    # Divergência
    # ------------------------------------------------------------------

    def test_divergencia_com_apuracao_fechada_bloqueia_validacao(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (19, 0))
        self._apurar_marco()
        holerite = self._holerite()
        holerite.l10n_br_horas_extras_50 = 10.0
        with self.assertRaises(UserError):
            holerite.action_payslip_done()

    def test_divergencia_justificada_passa(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (19, 0))
        self._apurar_marco()
        holerite = self._holerite()
        holerite.write(
            {
                "l10n_br_horas_extras_50": 10.0,
                "l10n_br_justificativa_divergencia": "Acordo de compensação do "
                "mês anterior, conforme ata do sindicato.",
            }
        )
        holerite.action_payslip_done()
        self.assertEqual(holerite.state, "done")

    def test_sem_apuracao_fechada_nao_ha_bloqueio(self):
        self._marcar(2, (8, 0), (12, 0), (13, 0), (19, 0))
        self._apurar_marco(fechar=False)
        holerite = self._holerite()
        holerite.l10n_br_horas_extras_50 = 10.0
        holerite.action_payslip_done()
        self.assertEqual(holerite.state, "done")

    def test_empresa_pode_desligar_o_bloqueio(self):
        self.company.l10n_br_bloqueia_holerite_divergente = False
        self._marcar(2, (8, 0), (12, 0), (13, 0), (19, 0))
        self._apurar_marco()
        holerite = self._holerite()
        holerite.l10n_br_horas_extras_50 = 10.0
        holerite.action_payslip_done()
        self.assertEqual(holerite.state, "done")
