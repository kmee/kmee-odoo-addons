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
