# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import importlib.util
import os

from odoo.modules import get_module_path
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMigracaoAsoDemissional(TransactionCase):
    """O ASO demissional passou do código 8 para o 9 (RS-30)."""

    def _migrar(self):
        caminho = os.path.join(
            get_module_path("l10n_br_esocial"),
            "migrations",
            "17.0.1.1.0",
            "post-migration.py",
        )
        spec = importlib.util.spec_from_file_location("post_migration_aso", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        modulo.migrate(self.env.cr, "17.0.1.0.0")

    def test_dado_novo_tem_codigo_9(self):
        tipo = self.env.ref("l10n_br_esocial.tipo_aso_9")
        self.assertEqual(tipo.codigo, "9")
        self.assertIn("Demissional", tipo.nome)
        self.assertFalse(
            self.env["l10n_br.esocial.tipo.aso"].search([("codigo", "=", "8")])
        )

    def test_migracao_remove_codigo_8_obsoleto(self):
        modelo = self.env["l10n_br.esocial.tipo.aso"]
        antigo = modelo.create(
            {"codigo": "8", "nome": "Demissional", "dt_inicio": "2014-01-01"}
        )
        self.env["ir.model.data"].create(
            {
                "module": "l10n_br_esocial",
                "name": "tipo_aso_8",
                "model": "l10n_br.esocial.tipo.aso",
                "res_id": antigo.id,
            }
        )
        self._migrar()
        self.assertFalse(antigo.exists())
        self.assertTrue(self.env.ref("l10n_br_esocial.tipo_aso_9"))

    def test_migracao_sem_dado_antigo_e_inocua(self):
        self._migrar()
        self.assertTrue(self.env.ref("l10n_br_esocial.tipo_aso_9").exists())
