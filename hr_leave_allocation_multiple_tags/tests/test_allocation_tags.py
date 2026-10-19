# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


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
        cls.work_entry_type = cls.env["hr.work.entry.type"].create(
            {
                "name": "Tagged leave",
                "code": "TAGGED",
                "requires_allocation": True,
                "employee_requests": False,
                "allocation_validation_type": "hr",
            }
        )

    def _wizard(self, mode, tags, **extra):
        vals = {
            "name": "Tag allocation",
            "work_entry_type_id": self.work_entry_type.id,
            "category_mode": mode,
            "category_ids": [(6, 0, tags.ids)],
            "duration": 5,
        }
        vals.update(extra)
        return self.env["hr.leave.allocation.generate.multi.wizard"].create(vals)

    def _employees(self, wizard):
        return self.env["hr.employee"].search(wizard._get_employee_domain())

    def _generate(self, mode, tags, **extra):
        action = self._wizard(mode, tags, **extra).action_generate_allocations()
        if not action:
            return self.env["hr.leave.allocation"]
        return self.env["hr.leave.allocation"].search(action["domain"])

    def test_category_mode_offers_and_or_modes(self):
        """
        Dado o campo category_mode do assistente de alocacao multipla
        Quando a selecao e lida
        Entao existem 'any' (OR) e 'all' (AND)
        """
        selection = dict(
            self.env["hr.leave.allocation.generate.multi.wizard"]
            ._fields["category_mode"]
            ._description_selection(self.env)
        )
        self.assertIn("any", selection)
        self.assertIn("all", selection)

    def test_category_any_matches_any_tag(self):
        wizard = self._wizard("any", self.tag_b)
        self.assertEqual(
            self._employees(wizard) & (self.emp_a | self.emp_ab), self.emp_ab
        )
        wizard = self._wizard("any", self.tag_a | self.tag_b)
        self.assertEqual(
            self._employees(wizard) & (self.emp_a | self.emp_ab),
            self.emp_a | self.emp_ab,
        )

    def test_category_all_matches_every_tag(self):
        wizard = self._wizard("all", self.tag_a | self.tag_b)
        self.assertEqual(
            self._employees(wizard) & (self.emp_a | self.emp_ab), self.emp_ab
        )

    def test_category_or_allocates_employees_with_any_tag(self):
        """
        Dado funcionarios com A, A+B e C
        Quando o assistente gera alocacoes 'qualquer das etiquetas (OR)' A,B
        Entao recebem Emp A e Emp AB, e nao Emp C
        """
        allocations = self._generate("any", self.tag_a | self.tag_b)
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
        allocations = self._generate("all", self.tag_a | self.tag_b)
        self.assertEqual(allocations.employee_id, self.emp_ab)

    def test_category_or_does_not_duplicate_employee_in_two_tags(self):
        """
        Dado Emp AB que tem as duas etiquetas
        Quando o assistente gera alocacoes OR A,B
        Entao Emp AB recebe UMA alocacao
        """
        allocations = self._generate("any", self.tag_a | self.tag_b)
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
        wizard = self._wizard("all", self.tag_a | empty_tag)
        self.assertFalse(self._employees(wizard))
        self.assertFalse(wizard.action_generate_allocations())
        self.assertFalse(
            self.env["hr.leave.allocation"].search(
                [("work_entry_type_id", "=", self.work_entry_type.id)]
            )
        )

    def test_explicit_employees_still_win(self):
        """
        Dado funcionarios escolhidos no assistente
        Quando ha etiquetas tambem
        Entao so os funcionarios informados recebem a alocacao
        """
        allocations = self._generate(
            "any", self.tag_a | self.tag_b, employee_ids=[(6, 0, self.emp_a.ids)]
        )
        self.assertEqual(allocations.employee_id, self.emp_a)

    def test_no_tags_keeps_standard_domain(self):
        wizard = self._wizard("any", self.env["hr.employee.category"])
        self.assertIn(self.emp_a, self._employees(wizard))
