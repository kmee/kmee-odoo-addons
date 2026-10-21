# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Substituição de funcionários.

Cobertura:
  - CRUD de substituição
  - Validação de datas
  - Titular != substituto
  - Workflow de estados
  - Departamento computado do titular
"""
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSubstituicao(TransactionCase):
    """Testes de substituição de funcionários."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dept = cls.env["hr.department"].create({"name": "TI"})
        cls.emp_titular = cls.env["hr.employee"].create(
            {"name": "Titular", "department_id": cls.dept.id}
        )
        cls.emp_substituto = cls.env["hr.employee"].create(
            {"name": "Substituto", "department_id": cls.dept.id}
        )

    def test_create_substituicao(self):
        """Cria substituição com campos obrigatórios."""
        sub = self.env["hr.substituicao"].create(
            {
                "employee_id": self.emp_titular.id,
                "substitute_employee_id": self.emp_substituto.id,
                "date_start": date(2024, 3, 1),
                "date_end": date(2024, 3, 15),
            }
        )
        self.assertEqual(sub.state, "draft")
        self.assertEqual(sub.department_id, self.dept)

    def test_department_computed_from_titular(self):
        """Departamento é computado a partir do titular."""
        sub = self.env["hr.substituicao"].create(
            {
                "employee_id": self.emp_titular.id,
                "substitute_employee_id": self.emp_substituto.id,
                "date_start": date(2024, 3, 1),
                "date_end": date(2024, 3, 15),
            }
        )
        self.assertEqual(sub.department_id, self.emp_titular.department_id)

    def test_same_employee_raises(self):
        """Titular e substituto não podem ser o mesmo funcionário."""
        with self.assertRaises(ValidationError):
            self.env["hr.substituicao"].create(
                {
                    "employee_id": self.emp_titular.id,
                    "substitute_employee_id": self.emp_titular.id,
                    "date_start": date(2024, 3, 1),
                    "date_end": date(2024, 3, 15),
                }
            )

    def test_invalid_dates_raises(self):
        """Data fim anterior à data início gera erro."""
        with self.assertRaises(ValidationError):
            self.env["hr.substituicao"].create(
                {
                    "employee_id": self.emp_titular.id,
                    "substitute_employee_id": self.emp_substituto.id,
                    "date_start": date(2024, 3, 15),
                    "date_end": date(2024, 3, 1),
                }
            )

    def test_workflow_draft_to_confirmed(self):
        """Transição draft → confirmed."""
        sub = self.env["hr.substituicao"].create(
            {
                "employee_id": self.emp_titular.id,
                "substitute_employee_id": self.emp_substituto.id,
                "date_start": date(2024, 3, 1),
                "date_end": date(2024, 3, 15),
            }
        )
        sub.action_confirm()
        self.assertEqual(sub.state, "confirmed")

    def test_workflow_confirmed_to_done(self):
        """Transição confirmed → done."""
        sub = self.env["hr.substituicao"].create(
            {
                "employee_id": self.emp_titular.id,
                "substitute_employee_id": self.emp_substituto.id,
                "date_start": date(2024, 3, 1),
                "date_end": date(2024, 3, 15),
            }
        )
        sub.action_confirm()
        sub.action_done()
        self.assertEqual(sub.state, "done")

    def test_workflow_cancel_and_back_to_draft(self):
        """Cancel e retorno a rascunho."""
        sub = self.env["hr.substituicao"].create(
            {
                "employee_id": self.emp_titular.id,
                "substitute_employee_id": self.emp_substituto.id,
                "date_start": date(2024, 3, 1),
                "date_end": date(2024, 3, 15),
            }
        )
        sub.action_cancel()
        self.assertEqual(sub.state, "cancelled")
        sub.action_draft()
        self.assertEqual(sub.state, "draft")

    def test_substituicao_with_leave(self):
        """Substituição pode ser vinculada a um afastamento."""
        sub = self.env["hr.substituicao"].create(
            {
                "employee_id": self.emp_titular.id,
                "substitute_employee_id": self.emp_substituto.id,
                "date_start": date(2024, 3, 1),
                "date_end": date(2024, 3, 15),
                "reason": "Férias do titular",
            }
        )
        self.assertEqual(sub.reason, "Férias do titular")
        self.assertFalse(sub.leave_id)
