# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestAllocationTags(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, tracking_disable=True, mail_notrack=True)
        )
        Category = cls.env["hr.employee.category"]
        cls.tag_a = Category.create({"name": "Tag A"})
        cls.tag_b = Category.create({"name": "Tag B"})
        cls.tag_c = Category.create({"name": "Tag C"})
        Employee = cls.env["hr.employee"]
        cls.emp_a = Employee.create(
            {"name": "Emp A", "category_ids": [(6, 0, cls.tag_a.ids)]}
        )
        cls.emp_ab = Employee.create(
            {"name": "Emp AB", "category_ids": [(6, 0, (cls.tag_a | cls.tag_b).ids)]}
        )
        cls.emp_c = Employee.create(
            {"name": "Emp C", "category_ids": [(6, 0, cls.tag_c.ids)]}
        )
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Tagged leave",
                "requires_allocation": "yes",
                "employee_requests": "no",
                "allocation_validation_type": "officer",
            }
        )

    def _allocation(self, holiday_type, tags, **extra):
        vals = {
            "name": "Tag allocation",
            "holiday_status_id": self.leave_type.id,
            "holiday_type": holiday_type,
            "category_ids": [(6, 0, tags.ids)],
            "number_of_days": 5,
        }
        vals.update(extra)
        return self.env["hr.leave.allocation"].create(vals)

    def _children(self, allocation):
        return self.env["hr.leave.allocation"].search(
            [("parent_id", "=", allocation.id)]
        )

    def test_holiday_type_offers_and_or_modes(self):
        """
        Dado o campo holiday_type da alocacao
        Quando a selecao e lida
        Entao existem 'category_and' e 'category_or' alem dos modos do core
        """
        selection = dict(
            self.env["hr.leave.allocation"]._fields["holiday_type"]._description_selection(
                self.env
            )
        )
        self.assertIn("category_and", selection)
        self.assertIn("category_or", selection)
        self.assertIn("category", selection)

    def test_category_or_allocates_employees_with_any_tag(self):
        """
        Dado funcionarios com A, A+B e C
        Quando uma alocacao 'qualquer das etiquetas (OR)' A,B e validada
        Entao recebem Emp A e Emp AB, e nao Emp C
        """
        allocation = self._allocation("category_or", self.tag_a | self.tag_b)
        allocation.action_validate()
        childs = self._children(allocation)
        self.assertEqual(childs.employee_id, self.emp_a | self.emp_ab)
        self.assertNotIn(self.emp_c, childs.employee_id)
        self.assertTrue(all(c.state == "validate" for c in childs))
        self.assertTrue(all(c.number_of_days == 5 for c in childs))

    def test_category_and_allocates_employees_with_all_tags(self):
        """
        Dado funcionarios com A, A+B e C
        Quando uma alocacao 'todas as etiquetas (AND)' A,B e validada
        Entao so Emp AB recebe
        """
        allocation = self._allocation("category_and", self.tag_a | self.tag_b)
        allocation.action_validate()
        self.assertEqual(self._children(allocation).employee_id, self.emp_ab)

    def test_category_or_does_not_duplicate_employee_in_two_tags(self):
        """
        Dado Emp AB que tem as duas etiquetas
        Quando uma alocacao OR A,B e validada
        Entao Emp AB recebe UMA alocacao
        """
        allocation = self._allocation("category_or", self.tag_a | self.tag_b)
        allocation.action_validate()
        childs = self._children(allocation).filtered(
            lambda c: c.employee_id == self.emp_ab
        )
        self.assertEqual(len(childs), 1)

    def test_and_with_tag_nobody_has_creates_no_children(self):
        """
        Dado uma etiqueta sem funcionarios e outra com funcionarios
        Quando uma alocacao AND com as duas e validada
        Entao nenhuma alocacao filha e criada
        """
        empty_tag = self.env["hr.employee.category"].create({"name": "Empty"})
        allocation = self._allocation("category_and", self.tag_a | empty_tag)
        allocation.action_validate()
        self.assertEqual(allocation.state, "validate")
        self.assertFalse(self._children(allocation))

    def test_tag_modes_require_at_least_one_tag(self):
        """
        Dado o modo AND/OR
        Quando a alocacao e criada sem etiquetas
        Entao ocorre ValidationError
        """
        for holiday_type in ("category_and", "category_or"):
            with self.assertRaises(ValidationError):
                self._allocation(holiday_type, self.env["hr.employee.category"])

    def test_department_mode_requires_department(self):
        """
        Dado o modo 'departamento'
        Quando a alocacao e criada sem departamento
        Entao ocorre ValidationError
        """
        with self.assertRaises(ValidationError):
            self.env["hr.leave.allocation"].create(
                {
                    "name": "No dept",
                    "holiday_status_id": self.leave_type.id,
                    "holiday_type": "department",
                    "number_of_days": 1,
                }
            )

    def test_category_mode_requires_category(self):
        """
        Dado o modo 'etiqueta' do core
        Quando a alocacao e criada sem etiqueta
        Entao ocorre ValidationError
        """
        with self.assertRaises(ValidationError):
            self.env["hr.leave.allocation"].create(
                {
                    "name": "No tag",
                    "holiday_status_id": self.leave_type.id,
                    "holiday_type": "category",
                    "number_of_days": 1,
                }
            )

    def test_employee_mode_requires_employee(self):
        """
        Dado o modo 'funcionario'
        Quando a alocacao e criada sem funcionario
        Entao ocorre ValidationError
        """
        with self.assertRaises(ValidationError):
            self.env["hr.leave.allocation"].create(
                {
                    "name": "No employee",
                    "holiday_status_id": self.leave_type.id,
                    "holiday_type": "employee",
                    "employee_ids": [(5, 0, 0)],
                    "number_of_days": 1,
                }
            )

    def test_company_mode_defaults_company_and_is_valid(self):
        """
        Dado o modo 'empresa'
        Quando a alocacao e criada sem informar a empresa
        Entao a empresa corrente e preenchida e a alocacao e valida
        """
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "Company",
                "holiday_status_id": self.leave_type.id,
                "holiday_type": "company",
                "number_of_days": 1,
            }
        )
        self.assertEqual(allocation.mode_company_id, self.env.company)

    def test_company_mode_without_company_is_rejected(self):
        """
        Dado uma alocacao de empresa existente
        Quando a empresa e apagada na gravacao
        Entao ocorre ValidationError
        """
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "Company",
                "holiday_status_id": self.leave_type.id,
                "holiday_type": "company",
                "number_of_days": 1,
            }
        )
        with self.assertRaises(ValidationError):
            allocation.mode_company_id = False

    def test_switching_to_tag_mode_clears_employee_and_company(self):
        """
        Dado uma alocacao de empresa (com etiquetas ja escolhidas)
        Quando o modo muda para 'qualquer etiqueta (OR)'
        Entao a empresa e os funcionarios sao limpos
        """
        allocation = self.env["hr.leave.allocation"].create(
            {
                "name": "Company",
                "holiday_status_id": self.leave_type.id,
                "holiday_type": "company",
                "number_of_days": 1,
            }
        )
        allocation.category_ids = self.tag_a
        self.assertEqual(allocation.mode_company_id, self.env.company)
        allocation.holiday_type = "category_or"
        self.assertFalse(allocation.mode_company_id)
        self.assertFalse(allocation.employee_ids)
        self.assertEqual(allocation.category_ids, self.tag_a)

    def test_duration_must_be_positive_for_regular_allocation(self):
        """
        Dado uma alocacao regular
        Quando o numero de dias e zero
        Entao o banco rejeita (constraint duration_check)
        """
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self._allocation(
                "category_or", self.tag_a, number_of_days=0, allocation_type="regular"
            )
