# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestSalaryRuleESocial(TransactionCase):
    """Testes dos campos eSocial em hr.salary.rule."""

    def test_esocial_fields_exist(self):
        """Campos eSocial devem existir em hr.salary.rule."""
        rule = self.env["hr.salary.rule"].search([], limit=1)
        self.assertTrue(rule, "Deve existir ao menos uma regra salarial")
        fields = rule._fields
        self.assertIn("l10n_br_esocial_cod_rubr", fields)
        self.assertIn("l10n_br_esocial_ide_tab_rubr", fields)
        self.assertIn("l10n_br_esocial_nat_rubr_id", fields)
        self.assertIn("l10n_br_esocial_tp_rubr", fields)
        self.assertIn("l10n_br_esocial_cod_inc_cp", fields)
        self.assertIn("l10n_br_esocial_cod_inc_irrf", fields)
        self.assertIn("l10n_br_esocial_cod_inc_fgts", fields)

    def test_salary_rule_nat_rubr_assignment(self):
        """Deve ser possível atribuir natureza de rubrica a uma regra."""
        nat_rubr = self.env.ref("l10n_br_esocial.nat_rubr_1000")
        rule = self.env["hr.salary.rule"].search([], limit=1)
        rule.write(
            {
                "l10n_br_esocial_cod_rubr": "SALARIO",
                "l10n_br_esocial_nat_rubr_id": nat_rubr.id,
                "l10n_br_esocial_tp_rubr": "1",
                "l10n_br_esocial_cod_inc_cp": "11",
                "l10n_br_esocial_cod_inc_irrf": "11",
                "l10n_br_esocial_cod_inc_fgts": "11",
            }
        )
        self.assertEqual(rule.l10n_br_esocial_cod_rubr, "SALARIO")
        self.assertEqual(rule.l10n_br_esocial_nat_rubr_id.codigo, "1000")
        self.assertEqual(rule.l10n_br_esocial_tp_rubr, "1")

    def test_employee_esocial_fields(self):
        """Campos eSocial devem existir em hr.employee."""
        emp = self.env["hr.employee"].search([], limit=1)
        if not emp:
            emp = self.env["hr.employee"].create({"name": "Test eSocial"})
        fields = emp._fields
        self.assertIn("l10n_br_esocial_matricula", fields)
        self.assertIn("l10n_br_esocial_categoria_id", fields)

    def test_employee_categoria_assignment(self):
        """Deve ser possível atribuir categoria trabalhador ao empregado."""
        cat = self.env.ref("l10n_br_esocial.cat_trab_101")
        emp = self.env["hr.employee"].create(
            {
                "name": "Test CLT",
                "l10n_br_esocial_matricula": "MAT001",
                "l10n_br_esocial_categoria_id": cat.id,
            }
        )
        self.assertEqual(emp.l10n_br_esocial_matricula, "MAT001")
        self.assertEqual(emp.l10n_br_esocial_categoria_id.codigo, "101")

    def test_contract_esocial_fields(self):
        """Campos eSocial devem existir em hr.contract."""
        fields = self.env["hr.contract"]._fields
        self.assertIn("l10n_br_esocial_motivo_deslig_id", fields)

    def test_company_esocial_fields(self):
        """Campos eSocial devem existir em res.company."""
        company = self.env.company
        fields = company._fields
        self.assertIn("l10n_br_esocial_tp_amb", fields)
        self.assertIn("l10n_br_esocial_class_trib_id", fields)
        self.assertIn("l10n_br_esocial_lotacao_id", fields)
        # Default should be produção restrita
        self.assertEqual(company.l10n_br_esocial_tp_amb, "2")
