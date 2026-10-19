# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged

from ..models.l10n_br_hr_caged import _normalize as caged_normalize, _num
from ..models.l10n_br_hr_dirf import _format_value, _normalize
from ..models.l10n_br_hr_sefip import _val
from .common import ArquivosGovernoCase


@tagged("post_install", "-at_install")
class TestHelpers(ArquivosGovernoCase):
    def test_normalize_removes_accents_and_pads(self):
        """Given accented text, Then it is ASCII, cut and padded to size."""
        self.assertEqual(_normalize("Ação São", 6), "Acao S")
        self.assertEqual(_normalize("ab", 4), "ab  ")
        self.assertEqual(_normalize(False), "")
        self.assertEqual(caged_normalize("é", 3, "0"), "e00")

    def test_numeric_formatters(self):
        """Given values, Then cents are zero padded and numbers truncated."""
        self.assertEqual(_format_value(-12.34), "000000000001234")
        self.assertEqual(_val(1.5, 6), "000150")
        self.assertEqual(_val(False, 4), "0000")
        self.assertEqual(_num(7, 3), "007")
        self.assertEqual(_num(12345, 3), "123")


@tagged("post_install", "-at_install")
class TestDirfBehavior(ArquivosGovernoCase):
    def _dirf(self, **vals):
        values = {
            "company_id": self.company.id,
            "ano_referencia": 2025,
            "ano_calendario": 2024,
        }
        values.update(vals)
        return self.env["l10n_br.hr.dirf"].create(values)

    def test_name_follows_year_and_company(self):
        """Given a DIRF, When the year changes, Then the name is recomputed."""
        dirf = self._dirf()
        self.assertEqual(dirf.name, "DIRF 2025 - %s" % self.company.name)
        dirf.ano_referencia = 2026
        self.assertIn("2026", dirf.name)

    def test_search_employees_by_year_state_and_company(self):
        """Given payslips of several years and states, Then only
        done payslips of the calendar year and company are used."""
        other = self._create_employee("Outro", "987.654.321-00")
        self._create_contract(other, "2023-01-01")
        paid = self._create_employee("Pago", "111.444.777-35")
        self._create_contract(paid, "2023-01-01")
        self._create_payslip("2024-05-10", amounts={"BRUTO": 100.0})
        self._create_payslip("2023-05-10", employee=other, amounts={"BRUTO": 100.0})
        self._create_payslip("2024-05-10", employee=paid, state="done")
        draft = self._create_employee("Rascunho", "222.333.444-05")
        self._create_contract(draft, "2023-01-01")
        self._create_payslip("2024-05-10", employee=draft, state="draft")
        dirf = self._dirf()
        dirf.action_buscar_funcionarios()
        self.assertEqual(dirf.employee_ids, self.employee | paid)

    def test_payslips_by_month_and_line_total(self):
        """Given payslips in March and April, Then the month filter and the
        line totals follow the period."""
        self._create_payslip("2024-03-10", amounts={"BRUTO": 1000.0, "INSS": 100.0})
        self._create_payslip("2024-04-10", amounts={"BRUTO": 2000.0})
        dirf = self._dirf()
        year = dirf._get_payslips_employee(self.employee)
        march = dirf._get_payslips_employee(self.employee, 3)
        self.assertEqual(len(year), 2)
        self.assertEqual(len(march), 1)
        self.assertEqual(dirf._get_line_total(year, "BRUTO"), 3000.0)
        self.assertEqual(dirf._get_line_total(march, "INSS"), 100.0)
        self.assertEqual(dirf._get_line_total(march, "IRRF"), 0.0)

    def test_legacy_layout_header_and_employee_records(self):
        """Given payslips, Then the legacy layout has the header records and,
        per employee, 12 monthly records of each kind; employees without
        payslips give nothing."""
        self.company.partner_id.cnpj_cpf = "73.145.637/0001-40"
        self._create_payslip("2024-03-10", amounts={"BRUTO": 1000.0, "INSS": 100.0})
        dirf = self._dirf()
        header = dirf._generate_header()
        self.assertEqual(header[0], "DIRF|2025|2024|N||")
        self.assertTrue(header[2].startswith("DECPJ|73145637000140|"))
        lines = dirf._generate_employee_data(self.employee)
        kinds = [line.split("|")[0] for line in lines]
        self.assertEqual(kinds.count("RTRT"), 12)
        self.assertEqual(kinds.count("RTPO"), 12)
        self.assertEqual(kinds.count("RTDP"), 12)
        self.assertIn("RTRT|000000000100000|", lines)
        self.assertEqual(dirf._generate_employee_data(self._create_employee("Sem")), [])

    def test_legacy_generator_builds_file_and_needs_employees(self):
        """Given employees, Then the legacy generator fills the file and opens
        the record; without employees it refuses."""
        self._create_payslip("2024-03-10", amounts={"BRUTO": 1000.0})
        dirf = self._dirf()
        with self.assertRaises(UserError):
            dirf._gerar_dirf_descontinuado()
        dirf.action_buscar_funcionarios()
        dirf._gerar_dirf_descontinuado()
        self.assertEqual(dirf.state, "open")
        self.assertTrue(dirf.file_content.endswith("FIMDirf|"))
        self.assertEqual(base64.b64decode(dirf.file_binary).decode(), dirf.file_content)
        self.assertTrue(dirf.file_name.startswith("DIRF_2025_"))


@tagged("post_install", "-at_install")
class TestSefipBehavior(ArquivosGovernoCase):
    def _sefip(self, **vals):
        values = {"company_id": self.company.id, "mes": "3", "ano": 2024}
        values.update(vals)
        return self.env["l10n_br.hr.sefip"].create(values)

    def test_defaults_and_name(self):
        """Given a SEFIP, Then defaults and the name carry the competence."""
        sefip = self._sefip()
        self.assertEqual(sefip.codigo_recolhimento, "115")
        self.assertEqual(sefip.codigo_fpas, "515")
        self.assertIn("SEFIP", sefip.name)
        self.assertIn("2024", sefip.name)

    def test_payslips_of_the_competence_only(self):
        """Given payslips in March, April and a draft one, Then only the done
        ones of the month are found; month 13 does not filter by month."""
        self._create_payslip("2024-03-10", amounts={"BRUTO": 1.0})
        self._create_payslip("2024-04-10", amounts={"BRUTO": 1.0})
        self._create_payslip("2024-03-11", state="draft")
        march = self._sefip()._buscar_holerites()
        self.assertEqual(len(march), 1)
        all_year = self._sefip(mes="13")._buscar_holerites()
        self.assertEqual(len(all_year & march), 1)
        self.assertIn(
            "2024-04-10", [str(date) for date in all_year.mapped("date_from")]
        )

    def test_legacy_records_and_generator(self):
        """Given a payslip, Then the legacy generator builds records 00, 10 and
        30 and links the payslips; without payslips it refuses."""
        self.company.partner_id.cnpj_cpf = "73.145.637/0001-40"
        sefip = self._sefip()
        with self.assertRaises(UserError):
            sefip._gerar_sefip_descontinuado()
        self._create_payslip(
            "2024-03-10", amounts={"BRUTO": 1000.0, "INSS": 100.0, "FGTS": 80.0}
        )
        self.assertTrue(sefip._generate_reg00().startswith("00"))
        self.assertTrue(sefip._generate_reg10().startswith("10 73145637000140"))
        sefip._gerar_sefip_descontinuado()
        self.assertEqual(sefip.state, "open")
        records = sefip.file_content.split("\r\n")
        self.assertEqual([r[:2] for r in records], ["00", "10", "30"])
        self.assertEqual(len(sefip.payslip_ids), 1)
        self.assertTrue(sefip.file_name.startswith("SEFIP_03_2024_"))
        payslip = sefip.payslip_ids
        self.assertEqual(sefip._get_line_total(payslip, "INSS"), 100.0)


@tagged("post_install", "-at_install")
class TestCagedBehavior(ArquivosGovernoCase):
    def _caged(self, **vals):
        values = {"company_id": self.company.id, "mes": "3", "ano": 2024}
        values.update(vals)
        return self.env["l10n_br.hr.caged"].create(values)

    def test_month_selection_has_no_thirteenth(self):
        """Given the CAGED month field, Then there is no 13th salary option."""
        options = dict(self.env["l10n_br.hr.caged"]._fields["mes"].selection)
        self.assertEqual(len(options), 12)
        self.assertNotIn("13", options)

    def test_movements_are_admissions_and_dismissals_of_the_month(self):
        """Given an admission and a dismissal in March, Then both are found and
        the other contract is not."""
        hired = self._create_employee("Admitido", "111.444.777-35")
        self._create_contract(hired, "2024-03-05")
        fired = self._create_employee("Demitido", "222.333.444-05")
        contract = self._create_contract(
            fired, "2020-01-01", date_end="2024-03-20", state="close"
        )
        found = self._caged()._buscar_movimentacoes()
        self.assertIn(contract, found)
        self.assertIn(hired.contract_ids, found)
        self.assertNotIn(self.contract, found)

    def test_legacy_generator_builds_records(self):
        """Given movements, Then the legacy generator writes A, B, C and Z
        records (10 for admission, 20 for dismissal); none refuses."""
        caged = self._caged(mes="7")
        with self.assertRaises(UserError):
            caged._gerar_caged_descontinuado()
        hired = self._create_employee("Admitido", "111.444.777-35")
        self._create_contract(hired, "2024-07-05")
        fired = self._create_employee("Demitido", "222.333.444-05")
        self._create_contract(fired, "2020-01-01", date_end="2024-07-20", state="close")
        caged._gerar_caged_descontinuado()
        records = caged.file_content.split("\r\n")
        self.assertEqual([r[0] for r in records], ["A", "B", "C", "C", "Z"])
        self.assertEqual(sorted(r[1:3] for r in records if r[0] == "C"), ["10", "20"])
        self.assertEqual(len(caged.contract_ids), 2)
        self.assertEqual(caged.state, "open")


@tagged("post_install", "-at_install")
class TestSecurityAndCompany(ArquivosGovernoCase):
    def _user(self, login, xmlid):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "groups_id": [(6, 0, [self.env.ref(xmlid).id])],
            }
        )

    def test_hr_user_reads_and_hr_manager_writes(self):
        """Given an HR user and an HR manager, Then the user only reads the
        records and the manager manages them."""
        user = self._user("gov_user", "hr.group_hr_user")
        manager = self._user("gov_manager", "hr.group_hr_manager")
        for model, vals in (
            ("l10n_br.hr.dirf", {"ano_referencia": 2025, "ano_calendario": 2024}),
            ("l10n_br.hr.sefip", {"mes": "1", "ano": 2024}),
            ("l10n_br.hr.caged", {"mes": "1", "ano": 2024}),
        ):
            vals["company_id"] = self.company.id
            record = self.env[model].create(vals)
            self.assertEqual(record.with_user(user).state, "draft")
            with self.assertRaises(AccessError):
                record.with_user(user).write({"state": "open"})
            with self.assertRaises(AccessError):
                self.env[model].with_user(user).create(dict(vals))
            record.with_user(manager).action_open()
            self.assertEqual(record.state, "open")

    def test_company_sefip_fields_defaults(self):
        """Given a company, Then the FPAS and centralization defaults exist."""
        company = self.env["res.company"].create({"name": "Nova Empresa"})
        self.assertEqual(company.l10n_br_codigo_fpas, "515")
        self.assertEqual(company.l10n_br_centralizadora, "0")
        self.assertFalse(company.l10n_br_codigo_outras_entidades)

    def test_views_load(self):
        """Given the module views, Then every form and list can be built."""
        for model in ("l10n_br.hr.dirf", "l10n_br.hr.sefip", "l10n_br.hr.caged"):
            for view_type in ("form", "tree"):
                arch = self.env[model].get_view(view_type=view_type)["arch"]
                self.assertTrue(arch)
