# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Tipos de afastamento CLT.

Cobertura:
  - Criação dos tipos de licença brasileiros via XML data
  - Campos CLT nos tipos de licença
  - Falta injustificada com payroll_discount e discount_dsr
  - Atestado médico exige comprovante
  - Licença-maternidade com limite de dias
"""
from odoo.tests.common import TransactionCase


class TestLeaveTypes(TransactionCase):
    """Testes dos tipos de afastamento CLT."""

    def test_leave_type_falta_injustificada(self):
        """Falta injustificada desconta folha e DSR."""
        lt = self.env.ref("l10n_br_hr_holiday.leave_type_falta_injustificada")
        self.assertTrue(lt.l10n_br_payroll_discount)
        self.assertTrue(lt.l10n_br_discount_dsr)
        self.assertEqual(lt.l10n_br_category, "unjustified")
        self.assertEqual(lt.code, "FALTA_INJUST")

    def test_leave_type_falta_justificada_sem_desconto(self):
        """Falta justificada sem desconto."""
        lt = self.env.ref("l10n_br_hr_holiday.leave_type_falta_justificada")
        self.assertFalse(lt.l10n_br_payroll_discount)
        self.assertFalse(lt.l10n_br_discount_dsr)
        self.assertEqual(lt.l10n_br_category, "justified")

    def test_leave_type_falta_justificada_com_desconto(self):
        """Falta justificada com desconto mas sem DSR."""
        lt = self.env.ref("l10n_br_hr_holiday.leave_type_falta_justificada_desconto")
        self.assertTrue(lt.l10n_br_payroll_discount)
        self.assertFalse(lt.l10n_br_discount_dsr)

    def test_leave_type_atestado_medico(self):
        """Atestado médico exige comprovante e não desconta."""
        lt = self.env.ref("l10n_br_hr_holiday.leave_type_atestado_medico")
        self.assertTrue(lt.l10n_br_need_attachment)
        self.assertFalse(lt.l10n_br_payroll_discount)
        self.assertEqual(lt.l10n_br_category, "disease")
        self.assertEqual(lt.l10n_br_days_limit, 15)

    def test_leave_type_maternidade(self):
        """Licença-maternidade: 120 dias sem desconto."""
        lt = self.env.ref("l10n_br_hr_holiday.leave_type_maternidade")
        self.assertEqual(lt.l10n_br_days_limit, 120)
        self.assertFalse(lt.l10n_br_payroll_discount)
        self.assertEqual(lt.l10n_br_category, "maternity")
        self.assertEqual(lt.code, "MATERNIDADE")

    def test_leave_type_paternidade(self):
        """Licença-paternidade: 5 dias sem desconto."""
        lt = self.env.ref("l10n_br_hr_holiday.leave_type_paternidade")
        self.assertEqual(lt.l10n_br_days_limit, 5)
        self.assertFalse(lt.l10n_br_payroll_discount)
        self.assertEqual(lt.l10n_br_category, "maternity")

    def test_leave_type_casamento(self):
        """Casamento: 3 dias, exige comprovante, sem desconto."""
        lt = self.env.ref("l10n_br_hr_holiday.leave_type_casamento")
        self.assertEqual(lt.l10n_br_days_limit, 3)
        self.assertTrue(lt.l10n_br_need_attachment)
        self.assertFalse(lt.l10n_br_payroll_discount)
        self.assertEqual(lt.l10n_br_category, "family")

    def test_leave_type_falecimento(self):
        """Falecimento: 2 dias, exige comprovante."""
        lt = self.env.ref("l10n_br_hr_holiday.leave_type_falecimento")
        self.assertEqual(lt.l10n_br_days_limit, 2)
        self.assertTrue(lt.l10n_br_need_attachment)
        self.assertEqual(lt.l10n_br_category, "family")

    def test_leave_type_doacao_sangue(self):
        """Doação de sangue: 1 dia por 12 meses."""
        lt = self.env.ref("l10n_br_hr_holiday.leave_type_doacao_sangue")
        self.assertEqual(lt.l10n_br_days_limit, 1)
        self.assertEqual(lt.l10n_br_category, "civic")

    def test_leave_type_acidente_trabalho(self):
        """Acidente de trabalho: sem limite fixo, exige atestado."""
        lt = self.env.ref("l10n_br_hr_holiday.leave_type_acidente_trabalho")
        self.assertTrue(lt.l10n_br_need_attachment)
        self.assertFalse(lt.l10n_br_payroll_discount)
        self.assertEqual(lt.l10n_br_category, "disease")

    def test_all_leave_types_have_code(self):
        """Todos os tipos de licença BR possuem código."""
        leave_types = self.env["hr.leave.type"].search(
            [("l10n_br_category", "!=", False)]
        )
        for lt in leave_types:
            self.assertTrue(
                lt.code,
                msg=f"Tipo de licença '{lt.name}' sem código definido",
            )

    def test_leave_type_custom_fields_on_create(self):
        """Campos CLT podem ser definidos ao criar tipo de licença."""
        lt = self.env["hr.leave.type"].create(
            {
                "name": "Teste Customizado",
                "code": "TESTE_CUSTOM",
                "l10n_br_category": "other",
                "l10n_br_need_attachment": True,
                "l10n_br_payroll_discount": True,
                "l10n_br_discount_dsr": True,
                "l10n_br_days_limit": 10,
                "requires_allocation": "no",
            }
        )
        self.assertEqual(lt.l10n_br_category, "other")
        self.assertTrue(lt.l10n_br_need_attachment)
        self.assertTrue(lt.l10n_br_payroll_discount)
        self.assertTrue(lt.l10n_br_discount_dsr)
        self.assertEqual(lt.l10n_br_days_limit, 10)
