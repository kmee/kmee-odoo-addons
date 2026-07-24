# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

try:
    import esociallib  # noqa: F401

    HAS_ESOCIALLIB = True
except ImportError:
    HAS_ESOCIALLIB = False
    _logger.warning("esociallib not installed — skipping XML generation tests")


class TestS1010XML(TransactionCase):
    """Testes do intermediário S-1010 (Tabela de Rubricas)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure company has CNPJ
        cls.company = cls.env.company
        partner = cls.company.partner_id
        if not partner.cnpj_cpf:
            partner.write({"cnpj_cpf": "02.546.716/0001-46"})

        # Get a salary rule and configure eSocial fields
        cls.rule = cls.env["hr.salary.rule"].search([], limit=1)
        cls.nat_rubr = cls.env.ref("l10n_br_esocial.nat_rubr_1000")
        cls.rule.write(
            {
                "l10n_br_esocial_cod_rubr": "SALARIO_BASE",
                "l10n_br_esocial_ide_tab_rubr": "1",
                "l10n_br_esocial_nat_rubr_id": cls.nat_rubr.id,
                "l10n_br_esocial_tp_rubr": "1",
                "l10n_br_esocial_cod_inc_cp": "11",
                "l10n_br_esocial_cod_inc_irrf": "11",
                "l10n_br_esocial_cod_inc_fgts": "11",
            }
        )

    def test_s1010_dict_structure(self):
        """Dict do S-1010 deve conter campos obrigatórios."""
        s1010 = self.env["l10n_br.esocial.s1010"].create(
            {
                "salary_rule_id": self.rule.id,
                "operacao": "inclusao",
                "ini_valid": "2024-01",
                "company_id": self.company.id,
            }
        )
        data = s1010._to_esociallib_dict()
        self.assertEqual(data["cod_rubr"], "SALARIO_BASE")
        self.assertEqual(data["nat_rubr"], 1000)
        self.assertEqual(data["tp_rubr"], 1)
        self.assertEqual(data["operacao"], "inclusao")
        self.assertEqual(data["ini_valid"], "2024-01")
        self.assertIn("tp_insc", data)
        self.assertIn("nr_insc", data)
        self.assertEqual(data["dsc_rubr"], self.rule.name)

    def test_s1010_missing_cod_rubr_raises(self):
        """Deve dar erro se regra não tem código rubrica."""
        rule2 = self.env["hr.salary.rule"].search([("id", "!=", self.rule.id)], limit=1)
        if not rule2:
            return
        rule2.l10n_br_esocial_cod_rubr = False
        s1010 = self.env["l10n_br.esocial.s1010"].create(
            {
                "salary_rule_id": rule2.id,
                "operacao": "inclusao",
                "ini_valid": "2024-01",
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(UserError):
            s1010._to_esociallib_dict()

    def test_s1010_gerar_xml(self):
        """Deve gerar XML válido via esociallib (se disponível)."""
        if not HAS_ESOCIALLIB:
            _logger.info("Skipping XML test — esociallib not installed")
            return
        s1010 = self.env["l10n_br.esocial.s1010"].create(
            {
                "salary_rule_id": self.rule.id,
                "operacao": "inclusao",
                "ini_valid": "2024-01",
                "company_id": self.company.id,
            }
        )
        xml = s1010._gerar_xml()
        self.assertIn("eSocial", xml)
        self.assertIn("SALARIO_BASE", xml)

    def test_s1010_gerar_evento(self):
        """Deve criar registro de evento ao gerar."""
        if not HAS_ESOCIALLIB:
            _logger.info("Skipping evento test — esociallib not installed")
            return
        s1010 = self.env["l10n_br.esocial.s1010"].create(
            {
                "salary_rule_id": self.rule.id,
                "operacao": "inclusao",
                "ini_valid": "2024-01",
                "company_id": self.company.id,
            }
        )
        evento = s1010.action_gerar_evento()
        self.assertEqual(evento.tipo, "S-1010")
        self.assertTrue(evento.xml_envio)
        self.assertEqual(evento.state, "draft")
        self.assertEqual(s1010.evento_id, evento)
