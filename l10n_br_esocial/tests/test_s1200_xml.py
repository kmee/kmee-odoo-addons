# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

try:
    pass

    HAS_ESOCIALLIB = True
except ImportError:
    HAS_ESOCIALLIB = False
    _logger.warning("esociallib not installed — skipping XML generation tests")


class TestS1200XML(TransactionCase):
    """Testes do intermediário S-1200 (Remuneração do Trabalhador)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        partner = cls.company.partner_id
        if not partner.cnpj_cpf:
            partner.write({"cnpj_cpf": "02.546.716/0001-46"})
        cls.company.l10n_br_esocial_cod_lotacao = "LOT001"

        # Configure categoria
        cls.cat_101 = cls.env.ref("l10n_br_esocial.cat_trab_101")

        # Create employee with eSocial fields
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Test eSocial Worker",
                "cnpj_cpf": "076.166.929-41",
                "l10n_br_esocial_matricula": "MAT001",
                "l10n_br_esocial_categoria_id": cls.cat_101.id,
            }
        )
        cls.contract = cls.env["hr.contract"].create(
            {
                "name": "Contrato Test S1200",
                "employee_id": cls.employee.id,
                "wage": 5000.0,
                "date_start": "2024-01-02",
                "state": "open",
            }
        )

        # Configure salary rule with eSocial fields
        cls.nat_rubr = cls.env.ref("l10n_br_esocial.nat_rubr_1000")
        cls.rule = cls.env["hr.salary.rule"].search(
            [("code", "=", "SALARIO_BASE")], limit=1
        )
        if not cls.rule:
            cls.rule = cls.env["hr.salary.rule"].search([], limit=1)
        cls.rule.write(
            {
                "l10n_br_esocial_cod_rubr": "SAL_BASE",
                "l10n_br_esocial_ide_tab_rubr": "1",
                "l10n_br_esocial_nat_rubr_id": cls.nat_rubr.id,
                "l10n_br_esocial_tp_rubr": "1",
                "l10n_br_esocial_cod_inc_cp": "11",
                "l10n_br_esocial_cod_inc_irrf": "11",
                "l10n_br_esocial_cod_inc_fgts": "11",
            }
        )

    def _create_s1200(self, payslip_ids=None):
        return self.env["l10n_br.esocial.s1200"].create(
            {
                "employee_id": self.employee.id,
                "payslip_ids": [(6, 0, payslip_ids or [])],
                "per_apur": "2024-03",
                "ind_apuracao": "1",
                "company_id": self.company.id,
            }
        )

    def test_s1200_dict_structure(self):
        """Dict do S-1200 deve conter campos obrigatórios."""
        s1200 = self._create_s1200()
        # Without payslips, should raise (no itens_remun)
        with self.assertRaises(UserError):
            s1200._to_esociallib_dict()

    def test_s1200_requires_categoria(self):
        """Deve dar erro se empregado não tem categoria."""
        emp2 = self.env["hr.employee"].create(
            {
                "name": "No Categoria Worker",
                "cnpj_cpf": "857.642.960-52",
                "l10n_br_esocial_matricula": "MAT002",
            }
        )
        s1200 = self.env["l10n_br.esocial.s1200"].create(
            {
                "employee_id": emp2.id,
                "per_apur": "2024-03",
                "ind_apuracao": "1",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s1200._to_esociallib_dict()

    def test_s1200_requires_cpf(self):
        """Deve dar erro se empregado não tem CPF."""
        emp3 = self.env["hr.employee"].create(
            {
                "name": "No CPF Worker",
                "l10n_br_esocial_matricula": "MAT003",
                "l10n_br_esocial_categoria_id": self.cat_101.id,
            }
        )
        s1200 = self.env["l10n_br.esocial.s1200"].create(
            {
                "employee_id": emp3.id,
                "per_apur": "2024-03",
                "ind_apuracao": "1",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s1200._to_esociallib_dict()

    def test_payslip_esocial_field_exists(self):
        """hr.payslip deve ter campo l10n_br_esocial_s1200_id."""
        fields = self.env["hr.payslip"]._fields
        self.assertIn("l10n_br_esocial_s1200_id", fields)

    # ── RF-25: robustez do S-1200 ──────────────────────────────────────────

    def _create_payslip_with_lines(self, amounts):
        """Cria um holerite com uma linha por valor em ``amounts``."""
        payslip = self.env["hr.payslip"].create(
            {
                "name": "Holerite Test",
                "employee_id": self.employee.id,
                "contract_id": self.contract.id,
                "date_from": "2024-03-01",
                "date_to": "2024-03-31",
            }
        )
        for i, amount in enumerate(amounts):
            self.env["hr.payslip.line"].create(
                {
                    "slip_id": payslip.id,
                    "salary_rule_id": self.rule.id,
                    "name": f"Linha {i}",
                    "code": f"L{i}",
                    "employee_id": self.employee.id,
                    "contract_id": self.contract.id,
                    "quantity": 1,
                    "amount": amount,
                    "rate": 100,
                }
            )
        return payslip

    def test_s1200_filtra_linhas_zeradas(self):
        """Linhas com total == 0 não devem ir para itens_remun."""
        payslip = self._create_payslip_with_lines([5000.0, 0.0])
        s1200 = self._create_s1200(payslip_ids=[payslip.id])
        itens = s1200._build_itens_remun()
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["vr_rubr"], "5000.0")

    def test_s1200_requires_matricula(self):
        """Deve dar erro se empregado não tem matrícula.

        A validação de matrícula ocorre antes da leitura das linhas, então
        não é necessário montar holerite para exercitá-la.
        """
        emp = self.env["hr.employee"].create(
            {
                "name": "No Matricula Worker",
                "cnpj_cpf": "857.642.960-52",
                "l10n_br_esocial_categoria_id": self.cat_101.id,
            }
        )
        s1200 = self.env["l10n_br.esocial.s1200"].create(
            {
                "employee_id": emp.id,
                "per_apur": "2024-03",
                "ind_apuracao": "1",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s1200._to_esociallib_dict()

    def test_s1200_retificacao_exige_nr_recibo(self):
        """ind_retif=2 sem nr_recibo deve levantar erro."""
        payslip = self._create_payslip_with_lines([5000.0])
        s1200 = self.env["l10n_br.esocial.s1200"].create(
            {
                "employee_id": self.employee.id,
                "payslip_ids": [(6, 0, [payslip.id])],
                "per_apur": "2024-03",
                "ind_apuracao": "1",
                "ind_retif": "2",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s1200._to_esociallib_dict()

    def test_s1200_retificacao_com_nr_recibo(self):
        """ind_retif=2 com nr_recibo deve popular o dict corretamente."""
        payslip = self._create_payslip_with_lines([5000.0])
        s1200 = self.env["l10n_br.esocial.s1200"].create(
            {
                "employee_id": self.employee.id,
                "payslip_ids": [(6, 0, [payslip.id])],
                "per_apur": "2024-03",
                "ind_apuracao": "1",
                "ind_retif": "2",
                "nr_recibo": "1.2.202403.0000001",
                "company_id": self.company.id,
            }
        )
        data = s1200._to_esociallib_dict()
        self.assertEqual(data["ind_retif"], 2)
        self.assertEqual(data["nr_recibo"], "1.2.202403.0000001")

    def test_s1200_original_sem_nr_recibo(self):
        """ind_retif=1 (original) não deve incluir nr_recibo."""
        payslip = self._create_payslip_with_lines([5000.0])
        s1200 = self._create_s1200(payslip_ids=[payslip.id])
        data = s1200._to_esociallib_dict()
        self.assertEqual(data["ind_retif"], 1)
        self.assertNotIn("nr_recibo", data)
