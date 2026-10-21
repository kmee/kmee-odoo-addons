# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

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
                "allocation_validation_type": "hr",
            }
        )

    def _wizard(self, mode, tags, **extra):
        vals = {
            "name": "Tag allocation",
            "holiday_status_id": self.leave_type.id,
            "allocation_mode": mode,
            "category_ids": [(6, 0, tags.ids)],
            "duration": 5,
        }
        vals.update(extra)
        return self.env["hr.leave.allocation.generate.multi.wizard"].create(vals)

    def _generate(self, mode, tags, **extra):
        action = self._wizard(mode, tags, **extra).action_generate_allocations()
        if not action:
            return self.env["hr.leave.allocation"]
        return self.env["hr.leave.allocation"].search(action["domain"])

    def test_allocation_mode_offers_and_or_modes(self):
        """
        Dado o campo allocation_mode do assistente de alocacao multipla
        Quando a selecao e lida
        Entao existem 'category_and' e 'category_or' alem dos modos do core
        """
        selection = dict(
            self.env["hr.leave.allocation.generate.multi.wizard"]
            ._fields["allocation_mode"]
            ._description_selection(self.env)
        )
        self.assertIn("category_and", selection)
        self.assertIn("category_or", selection)
        self.assertIn("category", selection)

    def test_category_or_allocates_employees_with_any_tag(self):
        """
        Dado funcionarios com A, A+B e C
        Quando o assistente gera alocacoes 'qualquer das etiquetas (OR)' A,B
        Entao recebem Emp A e Emp AB, e nao Emp C
        """
        allocations = self._generate("category_or", self.tag_a | self.tag_b)
        self.assertEqual(allocations.employee_id, self.emp_a | self.emp_ab)
        self.assertNotIn(self.emp_c, allocations.employee_id)
        self.assertTrue(all(a.state == "validate" for a in allocations))
        self.assertTrue(all(a.number_of_days == 5 for a in allocations))

    def test_category_and_allocates_employees_with_all_tags(self):
        """
        Dado funcionarios com A, A+B e C
        Quando o assistente gera alocacoes 'todas as etiquetas (AND)' A,B
        Entao so Emp AB recebe
        """
        allocations = self._generate("category_and", self.tag_a | self.tag_b)
        self.assertEqual(allocations.employee_id, self.emp_ab)

    def test_category_or_does_not_duplicate_employee_in_two_tags(self):
        """
        Dado Emp AB que tem as duas etiquetas
        Quando o assistente gera alocacoes OR A,B
        Entao Emp AB recebe UMA alocacao
        """
        allocations = self._generate("category_or", self.tag_a | self.tag_b)
        self.assertEqual(
            len(allocations.filtered(lambda a: a.employee_id == self.emp_ab)), 1
        )

    def test_and_with_tag_nobody_has_creates_no_allocation(self):
        """
        Dado uma etiqueta sem funcionarios e outra com funcionarios
        Quando o assistente gera alocacoes AND com as duas
        Entao nenhuma alocacao e criada
        """
        empty_tag = self.env["hr.employee.category"].create({"name": "Empty"})
        wizard = self._wizard("category_and", self.tag_a | empty_tag)
        self.assertFalse(wizard._get_employees_from_allocation_mode())
        self.assertFalse(wizard.action_generate_allocations())
        self.assertFalse(
            self.env["hr.leave.allocation"].search(
                [("holiday_status_id", "=", self.leave_type.id)]
            )
        )

    def test_core_category_mode_still_works(self):
        """
        Dado o modo 'etiqueta' do core
        Quando o assistente le os funcionarios da etiqueta A
        Entao vem Emp A e Emp AB
        """
        wizard = self._wizard(
            "category", self.env["hr.employee.category"], category_id=self.tag_a.id
        )
        self.assertEqual(
            wizard._get_employees_from_allocation_mode(), self.emp_a | self.emp_ab
        )

    def test_standard_mode_still_works(self):
        """
        Dado o modo 'funcionario' do core
        Quando o assistente le os funcionarios escolhidos
        Entao vem so os funcionarios informados
        """
        wizard = self._wizard(
            "employee",
            self.env["hr.employee.category"],
            employee_ids=[(6, 0, self.emp_a.ids)],
            duration=2,
        )
        self.assertEqual(wizard._get_employees_from_allocation_mode(), self.emp_a)

    def test_duration_must_be_positive_for_regular_allocation(self):
        """
        Dado uma alocacao regular gerada pelo assistente
        Quando o numero de dias e zero
        Entao o banco rejeita (constraint duration_check)
        """
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self._generate("category_or", self.tag_a, duration=0)
