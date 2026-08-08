# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMappingSped(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.conta = cls.env["account.account"].create(
            {
                "name": "Caixa geral",
                "code": "SPEDTEST1",
                "account_type": "asset_cash",
                "company_id": cls.env.company.id,
            }
        )
        cls.plan = cls.env["l10n_br.account.mapping.plan"].create(
            {
                "name": "Referencial Lucro Real",
                "sped_referential": True,
                "sped_plan_code": "1",
            }
        )
        cls.ref = cls.env["l10n_br.account.mapping.account"].create(
            {
                "plan_id": cls.plan.id,
                "code": "1.01.01.01.01",
                "name": "Caixa e Equivalentes",
                "account_ids": [(6, 0, [cls.conta.id])],
            }
        )
        cls.env.company.l10n_br_sped_referential_plan_id = cls.plan

    def test_i051_da_conta_mapeada(self):
        """A conta mapeada devolve o par COD_PLAN_REF/COD_CTA_REF do I051."""
        vals = self.conta.l10n_br_sped_referential_line()
        self.assertEqual(vals, {"COD_PLAN_REF": "1", "COD_CTA_REF": "1.01.01.01.01"})

    def test_i051_de_conta_nao_mapeada_vem_vazio(self):
        """I051 e opcional por conta: sem mapeamento, sem registro."""
        outra = self.env["account.account"].create(
            {
                "name": "Conta sem referencial",
                "code": "SPEDTEST2",
                "account_type": "expense",
                "company_id": self.env.company.id,
            }
        )
        self.assertEqual(outra.l10n_br_sped_referential_line(), {})

    def test_empresa_sem_plano_referencial(self):
        self.env.company.l10n_br_sped_referential_plan_id = False
        self.assertEqual(self.conta.l10n_br_sped_referential_line(), {})

    def test_referencial_exige_codigo_do_plano(self):
        """Plano marcado como referencial sem COD_PLAN_REF e recusado."""
        with self.assertRaises(ValidationError):
            self.env["l10n_br.account.mapping.plan"].create(
                {"name": "Referencial sem codigo", "sped_referential": True}
            )

    def test_dominio_do_campo_da_empresa(self):
        """O campo da empresa so aceita planos marcados como referenciais."""
        comum = self.env["l10n_br.account.mapping.plan"].create(
            {"name": "Plano comum de escritorio"}
        )
        field = self.env.company._fields["l10n_br_sped_referential_plan_id"]
        self.assertIn(("sped_referential", "=", True), field.domain)
        self.assertFalse(comum.sped_referential)
