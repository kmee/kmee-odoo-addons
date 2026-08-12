# Copyright (C) 2025 KMEE Informatica LTDA - Luis Felipe Miléo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import unittest

from odoo.tests import tagged

from odoo.addons.l10n_br_account.tests.common import AccountMoveBRCommon


@tagged("post_install", "-at_install")
class TestAccountMoveTemplate(AccountMoveBRCommon):
    @classmethod
    def setUpClass(cls):
        # O AccountMoveBRCommon exige o plano de contas do l10n_br_coa_simple
        # instalado (dependencia de teste implicita do l10n_br_account, ver
        # l10n_br_account/tests/common.py). Em bases sem a localizacao
        # completa, o setup quebra com KeyError no xmlid do chart template.
        # Pular com motivo explicito e melhor que falhar por infraestrutura:
        # a suite roda integralmente nos ambientes com o l10n-brazil completo.
        try:
            super().setUpClass()
        except (KeyError, ValueError) as err:
            # o env.ref levanta ValueError (External ID not found); o KeyError
            # cobre o cache miss do ormcache quando o xmlid nao existe
            if "l10n_br_coa_simple" in str(err):
                raise unittest.SkipTest(
                    "l10n_br_coa_simple nao instalado: a suite exige o plano "
                    "de contas brasileiro usado pelo AccountMoveBRCommon"
                ) from err
            raise
        cls.configure_normal_company_taxes()

        # Create accounts for testing
        cls.account_revenue = cls.env["account.account"].search(
            [
                ("company_id", "=", cls.company_data["company"].id),
                ("account_type", "=", "income"),
            ],
            limit=1,
        )
        cls.account_receivable = cls.env["account.account"].search(
            [
                ("company_id", "=", cls.company_data["company"].id),
                ("account_type", "=", "asset_receivable"),
            ],
            limit=1,
        )
        cls.account_icms_debit = cls.env["account.account"].create(
            {
                "name": "ICMS s/ Vendas",
                "code": "3.1.1.01.001",
                "account_type": "expense",
                "company_id": cls.company_data["company"].id,
            }
        )
        cls.account_icms_credit = cls.env["account.account"].create(
            {
                "name": "ICMS a Recolher",
                "code": "2.1.1.01.001",
                "account_type": "liability_current",
                "company_id": cls.company_data["company"].id,
            }
        )
        cls.account_ipi_debit = cls.env["account.account"].create(
            {
                "name": "IPI a Recuperar",
                "code": "1.1.5.01.001",
                "account_type": "asset_current",
                "company_id": cls.company_data["company"].id,
            }
        )
        cls.account_ipi_credit = cls.env["account.account"].create(
            {
                "name": "IPI a Recolher",
                "code": "2.1.1.02.001",
                "account_type": "liability_current",
                "company_id": cls.company_data["company"].id,
            }
        )

        # Create a sale template
        cls.sale_template = cls.env["l10n_br.account.move.template"].create(
            {
                "name": "Sale Template",
                "fiscal_operation_type": "out",
                "company_id": cls.company_data["company"].id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "sequence": 10,
                            "fiscal_field": "amount_fiscal",
                            "account_debit_id": cls.account_receivable.id,
                            "account_credit_id": cls.account_revenue.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "sequence": 20,
                            "fiscal_field": "icms_value",
                            "tax_domain": "icms",
                            "account_debit_id": cls.account_icms_debit.id,
                            "account_credit_id": cls.account_icms_credit.id,
                        },
                    ),
                ],
            }
        )

        # Link template to sale fiscal operation
        cls.fo_sale = cls.env.ref("l10n_br_fiscal.fo_venda")
        cls.fo_sale.account_move_template_id = cls.sale_template

    def _create_sale_invoice(self, post=False):
        """Helper to create a standard sale invoice."""
        return self.init_invoice(
            move_type="out_invoice",
            products=[self.product_a],
            document_type=self.env.ref("l10n_br_fiscal.document_55"),
            document_serie_id=self.empresa_lc_document_55_serie_1,
            fiscal_operation=self.fo_sale,
            fiscal_operation_lines=[self.env.ref("l10n_br_fiscal.fo_venda_venda")],
            post=post,
        )

    def test_sale_simple(self):
        """Test that posting a sale invoice generates double-entry lines."""
        move = self._create_sale_invoice()

        # Before posting: no double-entry lines
        de_lines_before = move.line_ids.filtered(lambda line: line.is_double_entry_line)
        self.assertFalse(de_lines_before)

        # Post the invoice
        move.action_post()

        # After posting: double-entry lines should exist
        de_lines = move.line_ids.filtered(lambda line: line.is_double_entry_line)
        self.assertTrue(de_lines, "Double-entry lines should be generated on post")

        # Lines should be balanced (sum of debits = sum of credits)
        total_debit = sum(de_lines.mapped("debit"))
        total_credit = sum(de_lines.mapped("credit"))
        self.assertAlmostEqual(
            total_debit,
            total_credit,
            places=2,
            msg="Double-entry lines must be balanced (D=C)",
        )

        # The lines should NOT be in invoice_line_ids
        self.assertFalse(
            de_lines & move.invoice_line_ids,
            "Double-entry lines should not appear in invoice_line_ids",
        )

    def test_no_template_configured(self):
        """Move with fiscal operation but no template generates no extra lines."""
        # Remove template from operation
        self.fo_sale.account_move_template_id = False
        move = self._create_sale_invoice(post=True)

        de_lines = move.line_ids.filtered(lambda line: line.is_double_entry_line)
        self.assertFalse(de_lines)

        # Restore for other tests
        self.fo_sale.account_move_template_id = self.sale_template

    def test_draft_clears_lines(self):
        """Resetting to draft should remove double-entry lines."""
        move = self._create_sale_invoice(post=True)

        de_lines = move.line_ids.filtered(lambda line: line.is_double_entry_line)
        self.assertTrue(de_lines)

        # Reset to draft
        move.button_draft()

        de_lines_after = move.line_ids.filtered(lambda line: line.is_double_entry_line)
        self.assertFalse(
            de_lines_after,
            "Double-entry lines should be removed when resetting to draft",
        )

    def test_hierarchical_template(self):
        """Parent template items are included, child takes precedence."""
        # Create parent template with ICMS item
        parent_template = self.env["l10n_br.account.move.template"].create(
            {
                "name": "Parent Template",
                "fiscal_operation_type": "out",
                "company_id": self.company_data["company"].id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "sequence": 10,
                            "fiscal_field": "icms_value",
                            "tax_domain": "icms",
                            "account_debit_id": self.account_icms_debit.id,
                            "account_credit_id": self.account_icms_credit.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "sequence": 20,
                            "fiscal_field": "ipi_value",
                            "tax_domain": "ipi",
                            "account_debit_id": self.account_ipi_debit.id,
                            "account_credit_id": self.account_ipi_credit.id,
                        },
                    ),
                ],
            }
        )

        # Create child template that overrides icms_value but inherits ipi_value
        child_template = self.env["l10n_br.account.move.template"].create(
            {
                "name": "Child Template",
                "fiscal_operation_type": "out",
                "company_id": self.company_data["company"].id,
                "parent_id": parent_template.id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "sequence": 10,
                            "fiscal_field": "amount_fiscal",
                            "account_debit_id": self.account_receivable.id,
                            "account_credit_id": self.account_revenue.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "sequence": 20,
                            "fiscal_field": "icms_value",
                            "tax_domain": "icms",
                            "account_debit_id": self.account_icms_debit.id,
                            "account_credit_id": self.account_icms_credit.id,
                        },
                    ),
                ],
            }
        )

        # Child has icms_value -> parent's icms_value should NOT be duplicated
        all_items = child_template._get_all_items()
        icms_items = all_items.filtered(lambda i: i.fiscal_field == "icms_value")
        self.assertEqual(
            len(icms_items),
            1,
            "icms_value should appear only once (child takes precedence)",
        )

        # ipi_value from parent should be inherited
        ipi_items = all_items.filtered(lambda i: i.fiscal_field == "ipi_value")
        self.assertEqual(len(ipi_items), 1, "ipi_value should be inherited from parent")

        # Total items: amount_fiscal + icms_value (child) + ipi_value (parent)
        self.assertEqual(len(all_items), 3)

    def test_zero_value_skipped(self):
        """Template items for fields with zero value should not generate lines."""
        # Create a template with ipi_value (which will be 0 for a simple sale)
        template_with_ipi = self.env["l10n_br.account.move.template"].create(
            {
                "name": "Template with IPI",
                "fiscal_operation_type": "out",
                "company_id": self.company_data["company"].id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "sequence": 10,
                            "fiscal_field": "ipi_value",
                            "tax_domain": "ipi",
                            "account_debit_id": self.account_ipi_debit.id,
                            "account_credit_id": self.account_ipi_credit.id,
                        },
                    ),
                ],
            }
        )
        self.fo_sale.account_move_template_id = template_with_ipi

        move = self._create_sale_invoice(post=True)

        # IPI is typically 0 for simple sale operations
        de_lines = move.line_ids.filtered(lambda line: line.is_double_entry_line)
        ipi_lines = de_lines.filtered(lambda line: "IPI" in (line.name or ""))

        # If IPI value is 0 on the line, no double entry should be created
        inv_line = move.invoice_line_ids[:1]
        if not inv_line.ipi_value:
            self.assertFalse(ipi_lines, "IPI lines should not be created when value=0")

        # Restore
        self.fo_sale.account_move_template_id = self.sale_template

    def test_recursion_constraint(self):
        """Circular parent references should be rejected."""
        template_a = self.env["l10n_br.account.move.template"].create(
            {"name": "A", "company_id": self.company_data["company"].id}
        )
        template_b = self.env["l10n_br.account.move.template"].create(
            {
                "name": "B",
                "parent_id": template_a.id,
                "company_id": self.company_data["company"].id,
            }
        )
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            template_a.parent_id = template_b

    def test_historico_padrao_no_item(self):
        """Item com historico padrao gera linhas com o texto do template."""
        history = self.env["l10n_br.account.history"].create(
            {
                "name": "Apropriacao ICMS",
                "template": "%{CAMPO} s/ doc. %{DOC} de %{PARCEIRO}",
                "code": "30",
            }
        )
        self.sale_template.item_ids.filtered(
            lambda i: i.fiscal_field == "icms_value"
        ).history_id = history

        move = self._create_sale_invoice(post=True)
        de_lines = move.line_ids.filtered(lambda line: line.is_double_entry_line)
        icms_lines = de_lines.filtered(lambda line: "ICMS" in (line.name or ""))

        self.assertTrue(icms_lines, "linhas de ICMS deveriam existir")
        for line in icms_lines:
            self.assertIn("s/ doc.", line.name)
            self.assertNotIn("%{", line.name, "variavel nao substituida vazou")
            self.assertIn(move.partner_id.name, line.name)
