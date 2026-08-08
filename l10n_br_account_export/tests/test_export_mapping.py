# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import AccountExportCommon


@tagged("post_install", "-at_install")
class TestExportMapping(AccountExportCommon):
    """Integracao do plano de destino com a exportacao.

    Usa o layout do Dominio como veiculo por ser o de estrutura mais bem
    conhecida; o mecanismo resolvido aqui (o _resolve_account do chassi) e o
    mesmo para os 21 layouts.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.plan = cls.env["l10n_br.account.mapping.plan"].create(
            {"name": "Escritorio Mapping", "company_id": cls.company.id}
        )
        # N:1 de verdade: as duas contas do fixture desaguam na mesma conta
        cls.dest = cls.env["l10n_br.account.mapping.account"].create(
            {
                "plan_id": cls.plan.id,
                "code": "90001",
                "name": "Resultado consolidado",
                "account_ids": [
                    (6, 0, [cls.account_debito.id, cls.account_credito.id])
                ],
            }
        )

    def _export_with_plan(self, moves=None, partial=False):
        export = self._create_export("dominio", moves or self.move, partial)
        export.config_id.mapping_plan_id = self.plan
        return export

    def test_layout_usa_o_codigo_do_plano(self):
        """Com plano no perfil, o arquivo sai com o codigo do destino."""
        export = self._export_with_plan()
        export.action_generate()
        partida = self._lines(export)[2].split("|")
        # N:1: debito e credito caem na MESMA conta do destino
        self.assertEqual(partida[3], "90001")
        self.assertEqual(partida[4], "90001")

    def test_sem_plano_vale_o_campo_simples(self):
        """Sem plano no perfil, o comportamento 1:1 de antes e mantido."""
        export = self._create_export("dominio", self.move)
        self.assertFalse(export.config_id.mapping_plan_id)
        export.action_generate()
        partida = self._lines(export)[2].split("|")
        self.assertEqual(partida[3], "1101")
        self.assertEqual(partida[4], "2201")

    def test_conta_fora_do_plano_gera_critica_com_o_nome_do_plano(self):
        """Conta mapeada no campo simples mas fora do plano e recusada."""
        conta_nova = self.env["account.account"].create(
            {
                "name": "Conta fora do plano",
                "code": self._free_account_code(),
                "account_type": "expense",
                "company_id": self.company.id,
                # tem o campo 1:1, mas o perfil usa plano: nao vale
                "l10n_br_export_code": "77777",
            }
        )
        move = self._create_move("2026-08-11", 200.0, account_debito=conta_nova)
        export = self._export_with_plan(move)
        with self.assertRaises(UserError) as cm:
            export.action_generate()
        self.assertIn("Escritorio Mapping", str(cm.exception))
        self.assertEqual(export.state, "draft")

    def test_dominio_completo_usa_nome_do_destino(self):
        """O 0200 sai com codigo e NOME da conta como o escritorio conhece."""
        export = self._create_export("dominio_completo", self.move)
        export.config_id.mapping_plan_id = self.plan
        export.action_generate()
        plano = self._text(export, contendo="plano_contas")
        self.assertIn("|90001|", plano)
        self.assertIn("Resultado consolidado", plano)
        # o nome da conta do Odoo nao vaza para o plano do destino
        self.assertNotIn(self.account_debito.name, plano)
