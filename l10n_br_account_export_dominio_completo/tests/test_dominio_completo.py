# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.l10n_br_account_export.tests.layout_case import LayoutCase


@tagged("post_install", "-at_install")
class TestDominioCompleto(LayoutCase):
    """Contrato completo do chassi aplicado ao layout Dominio com plano de contas."""

    _layout = "dominio_completo"
    _is_spreadsheet = False
    _fixed_width = None

    def test_entrega_tambem_o_plano_de_contas(self):
        """A variante completa manda o registro 0200 das contas usadas.

        E o que costuma garantir importacao sem ajuste manual: as contas passam
        a existir no destino.
        """
        export = self._run()
        self.assertEqual(len(export.attachment_ids), 2)
        plano = self._text(export, contendo="plano_contas")
        self.assertIn("|0200|", plano)
        self.assertIn("1101", plano)
        self.assertIn("2201", plano)

    def test_dominio_completo_usa_nome_do_destino(self):
        """O 0200 sai com codigo e NOME da conta como o escritorio conhece."""
        plan = self.env["l10n_br_account_mapping.plan"].create(
            {"name": "Escritorio Mapping", "company_id": self.company.id}
        )
        self.env["l10n_br_account_mapping.account"].create(
            {
                "plan_id": plan.id,
                "code": "90001",
                "name": "Resultado consolidado",
                "account_ids": [
                    (6, 0, [self.account_debito.id, self.account_credito.id])
                ],
            }
        )
        export = self._create_export("dominio_completo", self.move)
        export.config_id.mapping_plan_id = plan
        export.action_generate()
        plano = self._text(export, contendo="plano_contas")
        self.assertIn("|90001|", plano)
        self.assertIn("Resultado consolidado", plano)
        # o nome da conta do Odoo nao vaza para o plano do destino
        self.assertNotIn(self.account_debito.name, plano)
