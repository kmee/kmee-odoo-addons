# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.l10n_br_hr_sst.tests.common import SstCommon

from ..models import hr_contract as modelo_contrato


@tagged("post_install", "-at_install")
class TestPayrollSst(SstCommon):
    """RS-18 e RS-19: adicionais derivados do laudo e GILRAT adicional."""

    def test_insalubridade_vem_do_laudo(self):
        self.contract.invalidate_recordset()
        self.assertTrue(self.contract.l10n_br_insalubridade)
        self.assertEqual(self.contract.l10n_br_grau_insalubridade, "medio")
        self.assertFalse(self.contract.l10n_br_periculosidade)

    def test_grau_mais_gravoso_prevalece(self):
        self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ruido.id,
                "insalubridade": True,
                "grau_insalubridade": "maximo",
                "date_from": "2026-01-01",
            }
        )
        self.contract.invalidate_recordset()
        self.assertEqual(self.contract.l10n_br_grau_insalubridade, "maximo")

    def test_periculosidade_do_laudo(self):
        self.risco.write({"insalubridade": False, "grau_insalubridade": False})
        self.risco.periculosidade = True
        self.contract.invalidate_recordset()
        self.assertTrue(self.contract.l10n_br_periculosidade)
        self.assertFalse(self.contract.l10n_br_insalubridade)

    def test_divergencia_quando_contrato_sobrescreve(self):
        self.contract.invalidate_recordset()
        self.contract.l10n_br_insalubridade = False
        self.assertTrue(self.contract.l10n_br_sst_divergencia)

    def test_sem_divergencia_quando_bate_com_o_laudo(self):
        self.contract.invalidate_recordset()
        self.assertFalse(self.contract.l10n_br_sst_divergencia)

    def test_divergencia_de_grau(self):
        self.contract.invalidate_recordset()
        self.contract.l10n_br_grau_insalubridade = "minimo"
        self.assertIn("grau", self.contract.l10n_br_sst_divergencia)

    def test_contrato_sem_ambiente_preserva_o_que_ja_pagava(self):
        contrato = self.env["hr.contract"].create(
            {
                "name": "Contrato sem SST",
                "employee_id": self.employee.id,
                "wage": 2000.0,
                "date_start": "2026-01-02",
                "state": "draft",
                "l10n_br_periculosidade": True,
            }
        )
        self.assertTrue(contrato.l10n_br_periculosidade)

    def test_aliquota_gilrat_do_risco(self):
        self.contract.invalidate_recordset()
        self.assertEqual(self.contract.l10n_br_sst_aliquota_gilrat, 6.0)

    def test_aliquota_gilrat_sem_exposicao(self):
        self.risco.financiamento_aposent_id = False
        self.contract.invalidate_recordset()
        self.assertEqual(self.contract.l10n_br_sst_aliquota_gilrat, 0.0)

    def test_regra_de_gilrat_entra_na_estrutura_clt(self):
        estrutura = self.env.ref("l10n_br_hr_payroll.structure_clt")
        regra = self.env.ref("l10n_br_hr_payroll_sst.hr_rule_gilrat_adicional")
        self.assertIn(regra, estrutura.rule_ids)

    def test_regra_de_gilrat_e_encargo_patronal(self):
        regra = self.env.ref("l10n_br_hr_payroll_sst.hr_rule_gilrat_adicional")
        self.assertEqual(regra.category_id.code, "COMP")

    # ── Decisões normativas de 19/10/2026 ───────────────────────────────────

    def _risco_perigoso(self):
        return self.env["l10n_br.sst.risco"].create(
            {
                "ambiente_id": self.ambiente.id,
                "agente_nocivo_id": self.agente_ruido.id,
                "job_ids": [(6, 0, [self.job.id])],
                "periculosidade": True,
                "date_from": "2026-01-01",
            }
        )

    def test_sem_opcao_paga_o_adicional_de_maior_valor(self):
        """Laudo com os dois e sem opção: 30% de 3.000 supera 20% do mínimo."""
        self._risco_perigoso()
        self.contract.invalidate_recordset()
        self.assertTrue(self.contract.l10n_br_periculosidade)
        self.assertFalse(self.contract.l10n_br_insalubridade)

    def test_sem_opcao_insalubridade_maior_fica_a_insalubridade(self):
        self.risco.grau_insalubridade = "maximo"
        self.contract.wage = 1000.0
        self._risco_perigoso()
        self.contract.invalidate_recordset()
        self.assertTrue(self.contract.l10n_br_insalubridade)
        self.assertFalse(self.contract.l10n_br_periculosidade)

    def test_opcao_do_empregado_prevalece(self):
        """CLT, art. 193, par. 2: o empregado opta, e a opção é datada."""
        self._risco_perigoso()
        self.contract.write(
            {
                "l10n_br_sst_opcao_adicional": "insalubridade",
                "l10n_br_sst_opcao_data": "2026-01-02",
            }
        )
        self.contract.invalidate_recordset()
        self.assertTrue(self.contract.l10n_br_insalubridade)
        self.assertFalse(self.contract.l10n_br_periculosidade)
        self.assertFalse(self.contract.l10n_br_sst_divergencia)

    def test_opcao_exige_data(self):
        with self.assertRaises(ValidationError):
            self.contract.l10n_br_sst_opcao_adicional = "periculosidade"

    def test_os_dois_no_laudo_nao_e_divergencia(self):
        """Pagar só um dos dois, como manda a lei, não diverge do laudo."""
        self._risco_perigoso()
        self.contract.invalidate_recordset()
        self.assertTrue(self.contract.l10n_br_sst_insalubridade_laudo)
        self.assertTrue(self.contract.l10n_br_sst_periculosidade_laudo)
        self.assertFalse(self.contract.l10n_br_sst_divergencia)

    def test_contribuinte_individual_nao_gera_adicional(self):
        """Diretor sem vínculo (722): nem RAT nem adicional (Lei 10.666, art. 1)."""
        self.employee.l10n_br_esocial_categoria_id = self.env.ref(
            "l10n_br_esocial.cat_trab_722"
        )
        self.contract.invalidate_recordset()
        self.assertEqual(self.contract.l10n_br_sst_aliquota_gilrat, 0.0)

    def test_cooperado_de_producao_gera_adicional(self):
        self.employee.l10n_br_esocial_categoria_id = self.env.ref(
            "l10n_br_esocial.cat_trab_738"
        )
        self.contract.invalidate_recordset()
        self.assertEqual(self.contract.l10n_br_sst_aliquota_gilrat, 6.0)

    def test_aliquota_considera_o_periodo_da_folha(self):
        """O adicional segue o risco vigente no período, não o de hoje."""
        self.risco.date_to = "2026-03-31"
        aliquota = self.contract._l10n_br_sst_aliquota_gilrat_em
        self.assertEqual(aliquota(date(2026, 3, 1), date(2026, 3, 31)), 6.0)
        self.assertEqual(aliquota(date(2026, 4, 1), date(2026, 4, 30)), 0.0)

    def test_regra_de_gilrat_usa_o_periodo(self):
        regra = self.env.ref("l10n_br_hr_payroll_sst.hr_rule_gilrat_adicional")
        self.assertEqual(
            regra.condition_python.strip(), modelo_contrato.REGRA_GILRAT_CONDICAO
        )
        self.assertEqual(
            regra.amount_python_compute.strip(), modelo_contrato.REGRA_GILRAT_VALOR
        )
        self.assertIn("payslip.date_to", regra.condition_python)

    def _holerite(self, inicio, fim):
        self.contract.struct_id = self.env.ref("l10n_br_hr_payroll.structure_clt")
        holerite = self.env["hr.payslip"].create(
            {
                "name": "Holerite SST",
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "struct_id": self.contract.struct_id.id,
                "date_from": inicio,
                "date_to": fim,
                "company_id": self.env.company.id,
            }
        )
        holerite.compute_sheet()
        return holerite.line_ids.filtered(lambda line: line.code == "GILRAT_ADICIONAL")

    def test_holerite_cobra_o_adicional_do_periodo(self):
        """No holerite, vale o risco do período, mesmo que já tenha acabado."""
        self.risco.date_to = "2026-03-31"
        marco = self._holerite(date(2026, 3, 1), date(2026, 3, 31))
        self.assertTrue(marco)
        self.assertGreater(marco.total, 0.0)
        abril = self._holerite(date(2026, 4, 1), date(2026, 4, 30))
        self.assertFalse(abril.filtered("total"))
