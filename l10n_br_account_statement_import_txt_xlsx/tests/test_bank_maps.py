# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64encode
from datetime import datetime
from os import path

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

MODULE = "l10n_br_account_statement_import_txt_xlsx"


@tagged("post_install", "-at_install")
class TestBankMaps(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        if not cls.env.company.chart_template:
            cls.env["account.chart.template"].try_loading(
                "generic_coa", company=cls.env.company, install_demo=False
            )
        cls.brl = cls.env.ref("base.BRL")
        cls.brl.active = True
        cls.suspense = cls.env["account.account"].create(
            {"code": "987654", "name": "Suspense", "account_type": "asset_current"}
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Banco BRL",
                "type": "bank",
                "code": "BBRL",
                "currency_id": cls.brl.id,
                "suspense_account_id": cls.suspense.id,
            }
        )
        cls.parser = cls.env["account.statement.import.sheet.parser"].with_context(
            journal_id=cls.journal.id
        )

    def _map(self, name):
        return self.env.ref("%s.banco_%s_statement_map" % (MODULE, name))

    def _file(self, name):
        with open(
            path.join(path.dirname(__file__), "fixtures", name + ".xls"), "rb"
        ) as f:
            return f.read()

    def _parse(self, bank):
        currency, _account, statements = self.parser.parse(
            self._file(bank), self._map(bank), bank + ".xls"
        )
        self.assertEqual(currency, "BRL")
        self.assertEqual(len(statements), 1)
        return statements[0]

    def test_maps_are_registered_for_the_four_banks(self):
        """
        Given the module is installed
        When the statement maps are read
        Then ITAU, SANTANDER, SICRED and BTG maps exist with Brazilian number
        and date formats, and are noupdate (user changes survive upgrades)
        """
        expected = {
            "itau": "ITAU BRL [XLS]",
            "santander": "SANTANDER BRL [XLS]",
            "sicred": "SICRED BRL [XLS]",
            "btg": "BTG BRL [XLS]",
        }
        for bank, name in expected.items():
            statement_map = self._map(bank)
            self.assertEqual(statement_map.name, name)
            self.assertEqual(statement_map.float_thousands_sep, "dot")
            self.assertEqual(statement_map.float_decimal_sep, "comma")
            self.assertEqual(statement_map.timestamp_format, "%d/%m/%Y")
            data = self.env["ir.model.data"].search(
                [
                    ("module", "=", MODULE),
                    ("name", "=", "banco_%s_statement_map" % bank),
                ]
            )
            self.assertTrue(data.noupdate)

    def test_itau_file_is_parsed_with_amounts_and_balances(self):
        """
        Given an Itau export (9 header lines, then the column header)
        When it is parsed with the Itau map
        Then three transactions come out with Brazilian amounts, the
        description joins launch and origin, and balances are derived
        """
        statement = self._parse("itau")
        transactions = statement["transactions"]
        self.assertEqual(
            [(t["date"], t["amount"]) for t in transactions],
            [
                (datetime(2026, 10, 2), "1500.0"),
                (datetime(2026, 10, 5), "-45.9"),
                (datetime(2026, 10, 7), "-1200.0"),
            ],
        )
        self.assertEqual(transactions[0]["payment_ref"], "PIX RECEBIDO CLIENTE A 0001")
        # opening balance = first balance - first amount
        self.assertEqual(statement["balance_start"], 10000.0)
        self.assertEqual(statement["balance_end_real"], 10254.1)
        self.assertEqual(statement["date"].isoformat(), "2026-10-02")

    def test_santander_file_is_parsed_without_balance(self):
        """
        Given a Santander export (2 header lines, then the column header)
        When it is parsed with the Santander map
        Then both transactions come out with signed amounts and no balance
        """
        statement = self._parse("santander")
        self.assertEqual(
            [(t["date"], t["amount"]) for t in statement["transactions"]],
            [(datetime(2026, 10, 10), "-300.0"), (datetime(2026, 10, 12), "2000.0")],
        )
        self.assertEqual(
            statement["transactions"][1]["payment_ref"], "TED RECEBIDA 654321"
        )
        self.assertNotIn("balance_start", statement)

    def test_sicred_file_skips_header_and_footer_lines(self):
        """
        Given a Sicred export without column header (10 lines before the
        data and 17 footer lines)
        When it is parsed with the Sicred map (columns by position)
        Then only the three data lines are imported, never the footer
        """
        statement = self._parse("sicred")
        transactions = statement["transactions"]
        self.assertEqual(
            [(t["date"], t["amount"]) for t in transactions],
            [
                (datetime(2026, 10, 1), "500.0"),
                (datetime(2026, 10, 3), "-750.25"),
                (datetime(2026, 10, 4), "1000.0"),
            ],
        )
        self.assertEqual(transactions[1]["payment_ref"], "PAGAMENTO BOLETO 55")
        self.assertEqual(statement["balance_start"], 2000.0)
        self.assertEqual(statement["balance_end_real"], 2749.75)

    def test_btg_file_is_parsed_with_in_out_column(self):
        """
        Given a BTG export (12 lines, then the column header)
        When it is parsed with the BTG map
        Then the single Entradas/Saidas column gives signed amounts and
        balances
        """
        statement = self._parse("btg")
        self.assertEqual(
            [(t["date"], t["amount"]) for t in statement["transactions"]],
            [(datetime(2026, 10, 6), "-2000.0"), (datetime(2026, 10, 8), "12.34")],
        )
        self.assertEqual(statement["transactions"][1]["payment_ref"], "RENDIMENTO")
        self.assertEqual(statement["balance_start"], 10000.0)
        self.assertEqual(statement["balance_end_real"], 8012.34)

    def test_wrong_map_for_the_file_is_refused(self):
        """
        Given a Santander file
        When it is parsed with the Itau map
        Then parsing fails instead of importing wrong data silently
        """
        with self.assertRaises(IndexError):
            self.parser.parse(self._file("santander"), self._map("itau"), "x.xls")

    def test_itau_import_wizard_creates_statement(self):
        """
        Given an Itau file and the Itau map selected in the import wizard
        When the file is imported on a BRL bank journal
        Then one statement is created with three lines, the opening balance
        and the real closing balance of the file
        """
        wizard = (
            self.env["account.statement.import"]
            .with_context(journal_id=self.journal.id)
            .create(
                {
                    "statement_filename": "itau.xls",
                    "statement_file": b64encode(self._file("itau")),
                    "sheet_mapping_id": self._map("itau").id,
                }
            )
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.env["account.bank.statement"].search(
            [("journal_id", "=", self.journal.id)]
        )
        self.assertEqual(len(statement), 1)
        self.assertEqual(
            sorted(statement.line_ids.mapped("amount")), [-1200.0, -45.9, 1500.0]
        )
        self.assertEqual(statement.balance_start, 10000.0)
        self.assertEqual(statement.balance_end_real, 10254.1)

    def test_import_wizard_without_transactions_is_refused(self):
        """
        Given an Itau file of a period without any movement
        When it is imported with the Itau map
        Then the wizard raises UserError and no statement is created
        """
        wizard = (
            self.env["account.statement.import"]
            .with_context(journal_id=self.journal.id)
            .create(
                {
                    "statement_filename": "itau_vazio.xls",
                    "statement_file": b64encode(self._file("itau_vazio")),
                    "sheet_mapping_id": self._map("itau").id,
                }
            )
        )
        with self.assertRaises(UserError):
            wizard.with_context(
                account_statement_import_sheet_file_test=True
            ).import_file_button()
        self.assertFalse(
            self.env["account.bank.statement"].search(
                [("journal_id", "=", self.journal.id)]
            )
        )
