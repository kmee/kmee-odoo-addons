# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""A jornada apurada é dado pessoal: cada um vê só a sua."""

from datetime import date

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestSegurancaApuracao(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, no_reset_password=True))
        usuarios = cls.env["res.users"].with_context(tracking_disable=True)
        cls.user_a = usuarios.create(
            {
                "name": "Usuário A",
                "login": "apuracao_a",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.user_b = usuarios.create(
            {
                "name": "Usuário B",
                "login": "apuracao_b",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.user_rh = usuarios.create(
            {
                "name": "RH Ponto",
                "login": "apuracao_rh",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("hr_attendance.group_hr_attendance_officer").id,
                        ],
                    )
                ],
            }
        )
        funcionarios = cls.env["hr.employee"]
        cls.emp_a = funcionarios.create({"name": "Func A", "user_id": cls.user_a.id})
        cls.emp_b = funcionarios.create({"name": "Func B", "user_id": cls.user_b.id})
        dias = cls.env["l10n_br.hr.apuracao.dia"]
        cls.dia_a = dias.create({"employee_id": cls.emp_a.id, "date": date(2026, 3, 2)})
        cls.dia_b = dias.create({"employee_id": cls.emp_b.id, "date": date(2026, 3, 2)})

    def test_funcionario_ve_apenas_a_propria_apuracao(self):
        dias = self.env["l10n_br.hr.apuracao.dia"].with_user(self.user_a).search([])
        self.assertEqual(dias, self.dia_a)

    def test_funcionario_nao_le_apuracao_alheia(self):
        with self.assertRaises(AccessError):
            self.dia_b.with_user(self.user_a).read(["state"])

    def test_rh_ve_apuracao_de_todos_da_empresa(self):
        dias = self.env["l10n_br.hr.apuracao.dia"].with_user(self.user_rh).search([])
        self.assertIn(self.dia_a, dias)
        self.assertIn(self.dia_b, dias)
