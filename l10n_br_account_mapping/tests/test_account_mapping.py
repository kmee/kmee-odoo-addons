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
        cls.plan = cls.env["l10n_br_account_mapping.plan"].create(
            {"name": "Escritorio X"}
        )
        cls.destino = cls.env["l10n_br_account_mapping.account"].create(
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
            self.env["l10n_br_account_mapping.account"].create(
                {
                    "plan_id": self.plan.id,
                    "code": "41103",
                    "name": "Outra despesa",
                    "account_ids": [(6, 0, [self.conta_a.id])],
                }
            )

    def test_mesma_conta_em_planos_diferentes_e_permitida(self):
        """Multi-destino: em outro plano, a conta cai onde precisar."""
        plan2 = self.env["l10n_br_account_mapping.plan"].create(
            {"name": "Plano Referencial RFB"}
        )
        destino2 = self.env["l10n_br_account_mapping.account"].create(
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
                self.env["l10n_br_account_mapping.account"].create(
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

    def test_resolve_respeita_vigencia(self):
        """Retificadora de ano antigo usa a tabela da epoca, nao a atual."""
        from datetime import date

        self.destino.write(
            {"date_start": date(2023, 1, 1), "date_end": date(2024, 12, 31)}
        )
        # dentro da vigencia resolve; fora, nao
        self.assertEqual(
            self.plan.resolve(self.conta_a, date=date(2023, 6, 30)), self.destino
        )
        self.assertFalse(self.plan.resolve(self.conta_a, date=date(2022, 6, 30)))
        self.assertFalse(self.plan.resolve(self.conta_a, date=date(2025, 1, 1)))
        # sem data, o mapeamento vale independente da vigencia
        self.assertEqual(self.plan.resolve(self.conta_a), self.destino)

    def test_plano_de_outra_empresa_e_invisivel(self):
        """Sem a ir.rule o usuario da empresa A exportava pelo plano da B."""
        company_b = self.env["res.company"].create({"name": "Empresa B (teste)"})
        plan_b = self.env["l10n_br_account_mapping.plan"].create(
            {"name": "Plano da empresa B", "company_id": company_b.id}
        )
        user_a = self.env["res.users"].create(
            {
                "name": "Usuario da empresa A",
                "login": "usuario_empresa_a@example.com",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [
                    (6, 0, [self.env.ref("account.group_account_manager").id])
                ],
            }
        )
        Plan = self.env["l10n_br_account_mapping.plan"].with_user(user_a)
        visiveis = Plan.search([])
        self.assertNotIn(plan_b, visiveis)
        self.assertIn(self.plan, visiveis)  # plano sem empresa vale para todos
