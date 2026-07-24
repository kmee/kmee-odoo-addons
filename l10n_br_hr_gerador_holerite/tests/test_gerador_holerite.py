from datetime import date

from odoo.tests.common import TransactionCase


class TestGeradorHolerite(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env.ref("l10n_br_hr.demo_employee_joao")
        cls.contract = cls.env.ref("l10n_br_hr_contract.demo_contract_joao")

    def _create_wizard(self, **kwargs):
        vals = {
            "contract_id": self.contract.id,
            "mes_do_ano": "1",
            "ano": 2024,
            "quantity": 12,
        }
        vals.update(kwargs)
        return self.env["hr.payslip.generator"].create(vals)

    def test_generate_12_payslips(self):
        """Gera 12 holerites consecutivos."""
        wizard = self._create_wizard()
        result = wizard.action_generate()
        self.assertEqual(len(wizard.payslip_ids), 12)
        self.assertEqual(result["res_model"], "hr.payslip")

    def test_payslips_cover_full_year(self):
        """Verifica que os 12 holerites cobrem jan-dez."""
        wizard = self._create_wizard(mes_do_ano="1", ano=2024, quantity=12)
        wizard.action_generate()
        months = wizard.payslip_ids.sorted("date_from").mapped("date_from")
        self.assertEqual(months[0], date(2024, 1, 1))
        self.assertEqual(months[-1], date(2024, 12, 1))

    def test_payslips_are_computed(self):
        """Verifica que os holerites são calculados (têm linhas)."""
        wizard = self._create_wizard(quantity=1)
        wizard.action_generate()
        payslip = wizard.payslip_ids
        self.assertTrue(payslip.line_ids)

    def test_year_rollover(self):
        """Gera holerites que cruzam virada de ano."""
        wizard = self._create_wizard(mes_do_ano="11", ano=2024, quantity=4)
        wizard.action_generate()
        dates = wizard.payslip_ids.sorted("date_from").mapped("date_from")
        self.assertEqual(dates[0], date(2024, 11, 1))
        self.assertEqual(dates[-1], date(2025, 2, 1))

    def test_custom_quantity(self):
        """Gera quantidade customizada de holerites."""
        wizard = self._create_wizard(quantity=3)
        wizard.action_generate()
        self.assertEqual(len(wizard.payslip_ids), 3)

    def test_no_duplicate_on_second_run(self):
        """Gerar a mesma competência duas vezes não duplica holerites."""
        Payslip = self.env["hr.payslip"]
        domain = [
            ("contract_id", "=", self.contract.id),
            ("date_from", ">=", date(2024, 1, 1)),
            ("date_to", "<=", date(2024, 12, 31)),
        ]
        self._create_wizard(mes_do_ano="1", ano=2024, quantity=3).action_generate()
        count_after_first = Payslip.search_count(domain)
        self.assertEqual(count_after_first, 3)

        wizard2 = self._create_wizard(mes_do_ano="1", ano=2024, quantity=3)
        wizard2.action_generate()
        count_after_second = Payslip.search_count(domain)
        self.assertEqual(
            count_after_second,
            3,
            "Segunda geração não deve duplicar holerites da mesma competência",
        )
        self.assertFalse(
            wizard2.payslip_ids,
            "Nenhum holerite novo deve ser criado na segunda geração",
        )

    def test_invalid_quantity_rejected(self):
        """Quantidade inválida (zero ou acima do teto) é rejeitada."""
        from odoo.exceptions import UserError

        with self.assertRaises(UserError):
            self._create_wizard(quantity=0)
        with self.assertRaises(UserError):
            self._create_wizard(quantity=999)

    def test_date_to_is_last_day_of_month(self):
        """Verifica que date_to é o último dia do mês."""
        wizard = self._create_wizard(mes_do_ano="2", ano=2024, quantity=1)
        wizard.action_generate()
        payslip = wizard.payslip_ids
        # 2024 é bissexto, fevereiro tem 29 dias
        self.assertEqual(payslip.date_to, date(2024, 2, 29))
