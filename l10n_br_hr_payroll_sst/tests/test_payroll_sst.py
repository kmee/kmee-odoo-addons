# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.l10n_br_hr_sst.tests.common import SstCommon


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
