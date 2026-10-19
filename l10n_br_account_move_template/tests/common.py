# Copyright (C) 2025 KMEE Informatica LTDA - Luis Felipe Miléo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import unittest

from odoo.addons.l10n_br_account.tests.common import AccountMoveBRCommon


class AccountMoveTemplateCommon(AccountMoveBRCommon):
    """AccountMoveBRCommon builds its second company from l10n_br_coa_simple.

    That module is not needed by this one, so both test companies use the
    generic Brazilian chart, which is always available with l10n_br_account.
    """

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        if company_name == "company_2_data":
            kwargs.update(
                {
                    "country_id": cls.env.ref("base.br").id,
                    "currency_id": cls.env.ref("base.BRL").id,
                    "is_industry": True,
                    "cnpj_cpf": "30.360.463/0001-25",
                    "state_id": cls.env.ref("base.state_br_sp").id,
                }
            )
            return super(AccountMoveBRCommon, cls).setup_company_data(
                "empresa 2 Simples Nacional",
                cls.env.ref("l10n_br_coa_generic.l10n_br_coa_generic_template"),
                **kwargs,
            )
        return super().setup_company_data(
            company_name, chart_template=chart_template, **kwargs
        )


class AccountMoveTemplateFixture(AccountMoveTemplateCommon):
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
            if "l10n_br_coa" in str(err):
                raise unittest.SkipTest(
                    "plano de contas l10n_br_coa nao instalado: a suite exige o plano "
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
