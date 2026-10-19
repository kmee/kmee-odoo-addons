# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from decimal import Decimal

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

OFX_TEMPLATE = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1><SONRS><STATUS><CODE>0<SEVERITY>INFO</STATUS>
<DTSERVER>20240131<LANGUAGE>POR</SONRS></SIGNONMSGSRSV1>
<BANKMSGSRSV1><STMTTRNRS><TRNUID>1<STATUS><CODE>0<SEVERITY>INFO</STATUS>
<STMTRS><CURDEF>BRL<BANKACCTFROM><BANKID>001<ACCTID>{acct}<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST><DTSTART>20240101<DTEND>20240131
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20240110<TRNAMT>100.50<FITID>{acct}A
<NAME>Customer A<MEMO>Deposit</STMTTRN>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20240115<TRNAMT>-30.25<FITID>{acct}B
<NAME>Supplier B<MEMO>Payment</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL><BALAMT>500.00<DTASOF>20240131</LEDGERBAL>
</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""


@tagged("post_install", "-at_install")
class TestOfxInvertType(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.env.ref("base.BRL").active = True
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "OFX Bank",
                "type": "bank",
                "code": "OFXB",
                "currency_id": cls.env.ref("base.BRL").id,
            }
        )
        cls.wizard_model = cls.env["account.statement.import"]
        cls.ofx_data = OFX_TEMPLATE.format(acct="9001").encode()

    def _previous_statement(self, end_balance, date=None):
        statement = self.env["account.bank.statement"].create(
            {
                "name": "Previous",
                "journal_id": self.journal.id,
                "balance_start": 0.0,
                "date": date or fields.Date.today(),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "journal_id": self.journal.id,
                            "payment_ref": "p",
                            "amount": 1,
                        },
                    )
                ],
            }
        )
        statement.balance_end_real = end_balance
        statement.flush_recordset()
        self.assertEqual(statement.balance_end_real, end_balance)
        return statement

    def _import_wizard(self):
        """A real wizard record (other statement importers call ensure_one)."""
        return self.wizard_model.with_context(journal_id=self.journal.id).create(
            {
                "statement_file": base64.b64encode(self.ofx_data),
                "statement_filename": "x.ofx",
            }
        )

    def _transactions(self, journal=None):
        wiz = self.wizard_model.with_context(
            journal_id=journal.id if journal else False
        )
        ofx = wiz._check_ofx(self.ofx_data)
        return ofx, {t.id: t for t in ofx.account.statement.transactions}

    def test_default_journal_keeps_ofx_signs(self):
        """Given a journal with both flags off, When the OFX is checked,
        Then amounts and types stay as in the file."""
        ofx, trx = self._transactions(self.journal)
        self.assertEqual(trx["9001A"].amount, Decimal("100.50"))
        self.assertEqual(trx["9001A"].type, "credit")
        self.assertEqual(trx["9001B"].amount, Decimal("-30.25"))
        self.assertEqual(trx["9001B"].type, "debit")
        self.assertEqual(ofx.account.statement.balance, Decimal("500.00"))

    def test_no_journal_in_context_keeps_ofx_signs(self):
        """Given no journal in the context, When the OFX is checked, Then
        nothing is inverted even if another journal has the flag."""
        self.journal.reverse_balance_of_entries_ofx = True
        _ofx, trx = self._transactions(None)
        self.assertEqual(trx["9001A"].amount, Decimal("100.50"))
        self.assertEqual(trx["9001A"].type, "credit")

    def test_reverse_flag_swaps_type_and_sign(self):
        """Given a journal that reverses entries, When the OFX is checked,
        Then credit becomes debit with negated amount and vice versa."""
        self.journal.reverse_balance_of_entries_ofx = True
        _ofx, trx = self._transactions(self.journal)
        self.assertEqual(trx["9001A"].type, "debit")
        self.assertEqual(trx["9001A"].amount, Decimal("-100.50"))
        self.assertEqual(trx["9001B"].type, "credit")
        self.assertEqual(trx["9001B"].amount, Decimal("30.25"))

    def test_reverse_flag_changes_parsed_statement_lines(self):
        """Given the reverse flag, When the file is parsed, Then the line
        amounts handed to the importer are negated and the start balance
        follows the file balance minus the inverted total."""
        wiz = self._import_wizard()
        normal = wiz._parse_file(self.ofx_data)[0][2][0]
        self.journal.reverse_balance_of_entries_ofx = True
        reverted = wiz._parse_file(self.ofx_data)[0][2][0]
        self.assertEqual([t["amount"] for t in normal["transactions"]], [100.5, -30.25])
        self.assertEqual(
            [t["amount"] for t in reverted["transactions"]], [-100.5, 30.25]
        )
        self.assertAlmostEqual(normal["balance_start"], 500.0 - 70.25)
        self.assertAlmostEqual(reverted["balance_start"], 500.0 + 70.25)

    def test_ignore_balance_without_previous_statement(self):
        """Given ignore_ofx_balance and no earlier statement, When parsed,
        Then the file balance is discarded (zero end balance)."""
        self.journal.ignore_ofx_balance = True
        wiz = self._import_wizard()
        res = wiz._parse_file(self.ofx_data)[0][2][0]
        self.assertEqual(res["balance_end_real"], 0.0)
        self.assertAlmostEqual(res["balance_start"], -70.25)

    def test_ignore_balance_chains_from_previous_statement(self):
        """Given ignore_ofx_balance and a statement ending in 1000, When the
        file is parsed, Then the end balance is 1000 plus the net movement
        instead of the (wrong) balance written in the OFX."""
        self._previous_statement(1000.0)
        self.journal.ignore_ofx_balance = True
        wiz = self._import_wizard()
        res = wiz._parse_file(self.ofx_data)[0][2][0]
        self.assertAlmostEqual(res["balance_end_real"], 1070.25)
        self.assertNotAlmostEqual(res["balance_end_real"], 500.0)
        self.assertAlmostEqual(res["balance_start"], 1000.0)

    def test_ignore_balance_chains_from_latest_statement(self):
        """Given two earlier statements (old one ending in 200, newest ending
        in 1000), When the file is parsed with ignore_ofx_balance, Then the
        balance chains from the NEWEST statement."""
        self._previous_statement(200.0, date="2023-01-01")
        self._previous_statement(1000.0, date="2024-01-01")
        self.journal.ignore_ofx_balance = True
        wiz = self._import_wizard()
        res = wiz._parse_file(self.ofx_data)[0][2][0]
        self.assertAlmostEqual(res["balance_end_real"], 1070.25)

    def test_ignore_balance_with_reverse_uses_inverted_amounts(self):
        """Given both flags and a previous statement of 1000, When parsed,
        Then the balance accumulates the INVERTED amounts."""
        self._previous_statement(1000.0)
        self.journal.write(
            {"ignore_ofx_balance": True, "reverse_balance_of_entries_ofx": True}
        )
        wiz = self._import_wizard()
        res = wiz._parse_file(self.ofx_data)[0][2][0]
        self.assertAlmostEqual(res["balance_end_real"], 1000.0 - 70.25)

    def test_invalid_file_is_not_ofx(self):
        """Given garbage content, When checked with a journal, Then it is
        not treated as OFX (False) and no error is raised."""
        wiz = self._import_wizard()
        self.assertFalse(wiz._check_ofx(b"not an ofx file"))

    def test_full_import_creates_inverted_lines(self):
        """Given the reverse flag, When the file is imported through the
        wizard, Then the statement lines are created with inverted amounts."""
        self.journal.reverse_balance_of_entries_ofx = True
        self.journal.bank_account_id = self.env["res.partner.bank"].create(
            {
                "acc_number": "9002",
                "partner_id": self.env.company.partner_id.id,
            }
        )
        wiz = self.wizard_model.with_context(journal_id=self.journal.id).create(
            {
                "statement_file": base64.b64encode(
                    OFX_TEMPLATE.format(acct="9002").encode()
                ),
                "statement_filename": "x.ofx",
            }
        )
        action = wiz.import_file_button()
        self.assertTrue(action)
        lines = self.env["account.bank.statement.line"].search(
            [("journal_id", "=", self.journal.id)]
        )
        self.assertEqual(sorted(lines.mapped("amount")), [-100.5, 30.25])

    def test_journal_flags_default_false(self):
        """Given a new journal, Then both flags are off by default."""
        self.assertFalse(self.journal.reverse_balance_of_entries_ofx)
        self.assertFalse(self.journal.ignore_ofx_balance)
