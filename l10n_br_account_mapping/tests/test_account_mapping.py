# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAccountMapping(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Account = cls.env["account.account"]
        cls.conta_a = Account.create(
            {
                "name": "Despesa com frete",
                "code": "MAPTEST1",
                "account_type": "expense",
                "company_id": cls.env.company.id,
            }
        )
        cls.conta_b = Account.create(
            {
                "name": "Despesa com seguro",
                "code": "MAPTEST2",
                "account_type": "expense",
                "company_id": cls.env.company.id,
            }
        )
        cls.conta_fora = Account.create(
            {
                "name": "Conta nao mapeada",
                "code": "MAPTEST9",
                "account_type": "expense",
                "company_id": cls.env.company.id,
            }
        )
        cls.plan = cls.env["l10n_br.account.mapping.plan"].create(
            {"name": "Escritorio X"}
        )
        cls.destino = cls.env["l10n_br.account.mapping.account"].create(
            {
                "plan_id": cls.plan.id,
                "code": "41102",
                "name": "Despesas logisticas",
                "account_ids": [(6, 0, [cls.conta_a.id, cls.conta_b.id])],
            }
        )

    def test_resolve_n_para_1(self):
        """Duas contas do Odoo desaguam na mesma conta do destino."""
        self.assertEqual(self.plan.resolve(self.conta_a), self.destino)
        self.assertEqual(self.plan.resolve(self.conta_b), self.destino)
        self.assertEqual(self.plan.resolve(self.conta_a).code, "41102")
        self.assertEqual(self.plan.resolve(self.conta_a).name, "Despesas logisticas")

    def test_resolve_conta_nao_mapeada_vem_vazia(self):
        self.assertFalse(self.plan.resolve(self.conta_fora))
        self.assertFalse(self.plan.resolve(self.env["account.account"]))

    def test_ambiguidade_no_mesmo_plano_e_recusada(self):
        """A mesma conta do Odoo em duas contas do MESMO plano e ambigua."""
        with self.assertRaises(ValidationError):
            self.env["l10n_br.account.mapping.account"].create(
                {
                    "plan_id": self.plan.id,
                    "code": "41103",
                    "name": "Outra despesa",
                    "account_ids": [(6, 0, [self.conta_a.id])],
                }
            )

    def test_mesma_conta_em_planos_diferentes_e_permitida(self):
        """Multi-destino: em outro plano, a conta cai onde precisar."""
        plan2 = self.env["l10n_br.account.mapping.plan"].create(
            {"name": "Plano Referencial RFB"}
        )
        destino2 = self.env["l10n_br.account.mapping.account"].create(
            {
                "plan_id": plan2.id,
                "code": "3.11.01",
                "name": "Referencial de despesa",
                "account_ids": [(6, 0, [self.conta_a.id])],
            }
        )
        self.assertEqual(self.plan.resolve(self.conta_a), self.destino)
        self.assertEqual(plan2.resolve(self.conta_a), destino2)

    def test_codigo_unico_por_plano(self):
        """Dois registros com o mesmo codigo no mesmo plano sao recusados."""
        from psycopg2 import IntegrityError

        from odoo.tools import mute_logger

        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["l10n_br.account.mapping.account"].create(
                    {
                        "plan_id": self.plan.id,
                        "code": "41102",
                        "name": "Duplicada",
                    }
                )

    def test_unmapped_accounts(self):
        contas = self.conta_a | self.conta_b | self.conta_fora
        self.assertEqual(self.plan.unmapped_odoo_accounts(contas), self.conta_fora)

    def test_inverso_na_conta(self):
        """A partir da conta do Odoo se enxerga onde ela desagua."""
        self.assertIn(self.destino, self.conta_a.l10n_br_mapping_account_ids)

    def test_contadores_do_plano(self):
        self.assertEqual(self.plan.account_count, 1)
        self.assertEqual(self.plan.mapped_count, 2)
