# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Testes: Benefícios na Folha de Pagamento.

Cobertura:
  - Vale-Transporte com desconto máximo de 6%
  - Vale-Refeição não tributável
  - Vale-Alimentação não tributável
  - Plano de Saúde dedutível do IRRF
  - Integração benefícios × folha
"""
from datetime import date

from odoo.addons.l10n_br_hr_payroll.tests.common import PayrollCommon


class TestBeneficios(PayrollCommon):
    """Testes dos benefícios na folha de pagamento."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template_vt = cls.env.ref("l10n_br_hr_benefit.advantage_template_vt")
        cls.template_vr = cls.env.ref("l10n_br_hr_benefit.advantage_template_vr")
        cls.template_va = cls.env.ref("l10n_br_hr_benefit.advantage_template_va")
        cls.template_plano = cls.env.ref(
            "l10n_br_hr_benefit.advantage_template_plano_saude"
        )

    def _add_advantage(self, contract, template, amount):
        """Helper: adiciona benefício ao contrato."""
        return self.env["hr.contract.advantage"].create(
            {
                "contract_id": contract.id,
                "advantage_template_id": template.id,
                "amount": amount,
            }
        )

    def _create_payslip_benefit(self, employee, contract):
        """Helper: cria payslip para testes de benefícios."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": f"Holerite - {employee.name}",
                "employee_id": employee.id,
                "contract_id": contract.id,
                "struct_id": contract.struct_id.id,
                "date_from": date(2024, 3, 1),
                "date_to": date(2024, 3, 31),
                "company_id": self.env.company.id,
            }
        )
        payslip.compute_sheet()
        return payslip

    # ── Vale-Transporte ─────────────────────────────────────────

    def test_vt_desconto_menor_que_6_porcento(self):
        """VT menor que 6% do salário: desconta o valor integral."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        self._add_advantage(contract, self.template_vt, 100.00)
        payslip = self._create_payslip_benefit(emp, contract)
        desc_vt = self._get_line_total(payslip, "DESC_VT")
        # 6% de 5000 = 300. VT = 100 < 300 → desconta 100
        self.assertAlmostEqualMoney(desc_vt, 100.00)

    def test_vt_desconto_limitado_a_6_porcento(self):
        """VT maior que 6% do salário: desconta apenas 6%."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=2000.00)
        self._add_advantage(contract, self.template_vt, 200.00)
        payslip = self._create_payslip_benefit(emp, contract)
        desc_vt = self._get_line_total(payslip, "DESC_VT")
        # 6% de 2000 = 120. VT = 200 > 120 → desconta 120
        self.assertAlmostEqualMoney(desc_vt, 120.00)

    def test_vt_exatamente_6_porcento(self):
        """VT igual a 6%: desconta tudo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        self._add_advantage(contract, self.template_vt, 180.00)
        payslip = self._create_payslip_benefit(emp, contract)
        desc_vt = self._get_line_total(payslip, "DESC_VT")
        # 6% de 3000 = 180. VT = 180 → desconta 180
        self.assertAlmostEqualMoney(desc_vt, 180.00)

    def test_vt_zero_sem_desconto(self):
        """Sem VT configurado: nenhum desconto."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        payslip = self._create_payslip_benefit(emp, contract)
        desc_vt = self._get_line_total(payslip, "DESC_VT")
        self.assertEqual(desc_vt, 0.0)

    # ── Vale-Refeição ───────────────────────────────────────────

    def test_vr_informativo_nao_tributavel(self):
        """VR aparece como informativo e não compõe base do INSS."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        self._add_advantage(contract, self.template_vr, 800.00)
        payslip = self._create_payslip_benefit(emp, contract)
        vr = self._get_line_total(payslip, "VR_INFO")
        self.assertAlmostEqualMoney(vr, 800.00)
        # INSS deve ser calculado sobre o salário, não sobre salário + VR
        inss_com_vr = self._get_line_total(payslip, "INSS")
        # Recalcula sem VR para comparar
        emp2 = self._create_employee(name="Sem VR")
        contract2 = self._create_contract(emp2, wage=3000.00)
        payslip2 = self._create_payslip_benefit(emp2, contract2)
        inss_sem_vr = self._get_line_total(payslip2, "INSS")
        self.assertAlmostEqualMoney(inss_com_vr, inss_sem_vr)

    # ── Vale-Alimentação ────────────────────────────────────────

    def test_va_informativo(self):
        """VA aparece como informativo."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=3000.00)
        self._add_advantage(contract, self.template_va, 600.00)
        payslip = self._create_payslip_benefit(emp, contract)
        va = self._get_line_total(payslip, "VA_INFO")
        self.assertAlmostEqualMoney(va, 600.00)

    # ── Plano de Saúde ──────────────────────────────────────────

    def test_plano_saude_desconta_do_salario(self):
        """Coparticipação do plano de saúde é descontada do salário."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        self._add_advantage(contract, self.template_plano, 150.00)
        payslip = self._create_payslip_benefit(emp, contract)
        desc = self._get_line_total(payslip, "DESC_PLANO_SAUDE")
        self.assertAlmostEqualMoney(desc, 150.00)

    def test_plano_saude_nao_altera_base_irrf(self):
        """Plano de saúde NÃO altera a base do IRRF na retenção mensal.

        Fisco (Fix 1): a coparticipação/mensalidade de plano de saúde não é
        dedutível na retenção do IRRF na fonte — só é dedutível na Declaração
        de Ajuste Anual (art. 4º Lei 9.250/95; art. 677 RIR/2018; art. 52 IN
        RFB 1.500/2014). O desconto DESC_PLANO_SAUDE reduz o líquido (categoria
        DED), mas a BASE_IRRF permanece a mesma. O override que reduzia a base
        foi removido em data/hr_payroll_structure_data.xml.
        """
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        # Sem plano
        payslip_sem = self._create_payslip_benefit(emp, contract)
        irrf_sem = self._get_line_total(payslip_sem, "IRRF")
        # Com plano
        self._add_advantage(contract, self.template_plano, 500.00)
        payslip_com = self._create_payslip_benefit(emp, contract)
        irrf_com = self._get_line_total(payslip_com, "IRRF")
        # IRRF deve ser IGUAL com e sem plano (base inalterada).
        self.assertAlmostEqualMoney(
            irrf_com,
            irrf_sem,
            msg="Plano de saúde não pode alterar a base/IRRF na fonte",
        )

    # ── Integração ──────────────────────────────────────────────

    def test_beneficios_nao_alteram_gross(self):
        """Benefícios INFO não alteram o GROSS."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        self._add_advantage(contract, self.template_vr, 800.00)
        self._add_advantage(contract, self.template_va, 600.00)
        payslip = self._create_payslip_benefit(emp, contract)
        gross = self._get_line_total(payslip, "GROSS")
        self.assertAlmostEqualMoney(gross, 5000.00)

    def test_beneficios_ded_reduzem_net(self):
        """Benefícios DED reduzem o líquido."""
        emp = self._create_employee()
        contract = self._create_contract(emp, wage=5000.00)
        # Folha sem benefícios
        payslip_sem = self._create_payslip_benefit(emp, contract)
        net_sem = self._get_line_total(payslip_sem, "NET")
        # Folha com VT + plano
        self._add_advantage(contract, self.template_vt, 200.00)
        self._add_advantage(contract, self.template_plano, 150.00)
        payslip_com = self._create_payslip_benefit(emp, contract)
        net_com = self._get_line_total(payslip_com, "NET")
        self.assertLess(net_com, net_sem)
