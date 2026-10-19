# Copyright (C) 2025 KMEE Informatica LTDA - Luis Felipe Miléo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from types import SimpleNamespace

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import AccountMoveTemplateFixture

MOVE_LOGGER = "odoo.addons.l10n_br_account_move_template.models.account_move"


@tagged("post_install", "-at_install")
class TestAccountMoveTemplateBehavior(AccountMoveTemplateFixture):
    def _template(self, items, **vals):
        values = {
            "name": "Behavior Template",
            "fiscal_operation_type": "out",
            "company_id": self.company_data["company"].id,
            "item_ids": [(0, 0, dict(item)) for item in items],
        }
        values.update(vals)
        return self.env["l10n_br.account.move.template"].create(values)

    def _item(self, fiscal_field, debit=None, credit=None, **vals):
        values = {"fiscal_field": fiscal_field}
        if debit:
            values["account_debit_id"] = debit.id
        if credit:
            values["account_credit_id"] = credit.id
        values.update(vals)
        return values

    def _draft_move(self, template=None):
        """Draft sale invoice linked to ``template`` with fiscal values set."""
        self.fo_sale.account_move_template_id = template or self.sale_template
        move = self._create_sale_invoice()
        line = move.invoice_line_ids[:1]
        line.write({"icms_value": 120.0, "ipi_value": 30.0, "freight_value": 10.0})
        return move, line

    def _de_lines(self, move):
        return move.line_ids.filtered("is_double_entry_line")

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------
    def test_one_balanced_pair_per_item_with_value(self):
        """Given ICMS (120) and fiscal amount items, When posting, Then each
        item produces one debit/credit pair with the item value and the
        configured accounts, labelled with the field name."""
        move, line = self._draft_move()
        move.action_post()
        icms = self._de_lines(move).filtered(lambda ln: "ICMS" in ln.name)
        self.assertEqual(len(icms), 2)
        debit = icms.filtered("debit")
        credit = icms.filtered("credit")
        self.assertEqual(debit.account_id, self.account_icms_debit)
        self.assertEqual(credit.account_id, self.account_icms_credit)
        self.assertGreater(line.icms_value, 0.0)
        self.assertEqual(debit.debit, line.icms_value)
        self.assertEqual(credit.credit, line.icms_value)
        self.assertTrue(debit.name.startswith("[ICMS próprio]"))
        self.assertEqual(debit.partner_id, move.partner_id)

    def test_generated_lines_are_not_invoice_lines_and_move_stays_balanced(self):
        """Given a posted invoice, Then the generated lines are accounting only
        and the whole move stays balanced."""
        move, line = self._draft_move()
        move.action_post()
        self.assertTrue(self._de_lines(move))
        self.assertFalse(self._de_lines(move) & move.invoice_line_ids)
        self.assertAlmostEqual(
            sum(move.line_ids.mapped("debit")),
            sum(move.line_ids.mapped("credit")),
            places=2,
        )

    def test_receivable_account_pair_gets_payment_term_type(self):
        """Given a template that debits the receivable account, Then that line
        is a payment_term line with a maturity date and the other is cogs."""
        move, line = self._draft_move()
        move.action_post()
        amount = self._de_lines(move).filtered(
            lambda ln: ln.account_id == self.account_receivable
        )
        self.assertEqual(amount.display_type, "payment_term")
        self.assertTrue(amount.date_maturity)
        other = self._de_lines(move) - amount
        self.assertEqual(set(other.mapped("display_type")), {"cogs"})

    def test_repost_regenerates_without_duplicating(self):
        """Given a posted invoice, When it goes back to draft and is posted
        again, Then the generated lines exist exactly once (never doubled)."""
        move, line = self._draft_move()
        move.action_post()
        first = len(self._de_lines(move))
        move.button_draft()
        self.assertFalse(self._de_lines(move))
        move.action_post()
        self.assertEqual(len(self._de_lines(move)), first)
        move._generate_double_entry_lines()
        self.assertEqual(len(self._de_lines(move)), first)

    def test_same_fiscal_field_in_two_items_is_generated_once(self):
        """Given two items on icms_value, Then only the first one generates
        entries (the field is done)."""
        template = self._template(
            [
                self._item(
                    "icms_value",
                    self.account_icms_debit,
                    self.account_icms_credit,
                    sequence=10,
                ),
                self._item(
                    "icms_value",
                    self.account_ipi_debit,
                    self.account_ipi_credit,
                    sequence=20,
                ),
            ]
        )
        move, line = self._draft_move(template)
        move.action_post()
        lines = self._de_lines(move)
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            set(lines.mapped("account_id")),
            {self.account_icms_debit, self.account_icms_credit},
        )

    def test_template_without_items_or_without_invoice_lines_does_nothing(self):
        """Given a template without items, Then posting generates no extra
        lines and does not fail."""
        template = self._template([])
        move, line = self._draft_move(template)
        move.action_post()
        self.assertFalse(self._de_lines(move))
        self.assertEqual(move.state, "posted")

    def test_items_are_generated_following_the_sequence(self):
        """Given items with sequences 30 (ICMS) and 10 (IPI), Then the IPI
        lines are created before the ICMS ones."""
        template = self._template(
            [
                self._item(
                    "icms_value",
                    self.account_icms_debit,
                    self.account_icms_credit,
                    sequence=30,
                ),
                self._item(
                    "ipi_value",
                    self.account_ipi_debit,
                    self.account_ipi_credit,
                    sequence=10,
                ),
            ]
        )
        move, line = self._draft_move(template)
        move.action_post()
        names = self._de_lines(move).sorted("id").mapped("name")
        self.assertIn("IPI", names[0])
        self.assertIn("ICMS", names[-1])

    # ------------------------------------------------------------------
    # Account resolution
    # ------------------------------------------------------------------
    def test_resolution_explicit_account_wins(self):
        """Given an item with explicit accounts, Then they are used."""
        move, line = self._draft_move()
        item = self.sale_template.item_ids.filtered(
            lambda i: i.fiscal_field == "icms_value"
        )
        self.assertEqual(
            move._resolve_account(line, item, "debit"), self.account_icms_debit
        )
        self.assertEqual(
            move._resolve_account(line, item, "credit"), self.account_icms_credit
        )

    def test_resolution_item_level_field_uses_product_income_account(self):
        """Given an item-level field (amount_fiscal) without accounts on a
        sale, Then the product income account is used."""
        template = self._template([self._item("amount_fiscal")])
        move, line = self._draft_move(template)
        item = template.item_ids
        expected = (
            line.product_id.property_account_income_id
            or line.product_id.categ_id.property_account_income_categ_id
        )
        self.assertTrue(expected)
        self.assertEqual(move._resolve_account(line, item, "debit"), expected)

    def test_resolution_document_level_field_uses_partner_receivable(self):
        """Given a document-level field (freight) without accounts on a sale,
        Then the partner receivable account is used for both sides."""
        template = self._template([self._item("freight_value")])
        move, line = self._draft_move(template)
        item = template.item_ids
        receivable = move.partner_id.property_account_receivable_id
        self.assertTrue(receivable)
        self.assertEqual(move._resolve_account(line, item, "credit"), receivable)

    def test_resolution_falls_back_to_journal_default_account(self):
        """Given a partner without receivable account, Then the journal default
        account is used."""
        template = self._template([self._item("freight_value")])
        move, line = self._draft_move(template)
        move.partner_id.property_account_receivable_id = False
        item = template.item_ids
        self.assertEqual(
            move._resolve_account(line, item, "debit"),
            move.journal_id.default_account_id,
        )

    @mute_logger(MOVE_LOGGER)
    def test_unresolvable_account_skips_the_item(self):
        """Given no account anywhere, Then the item generates nothing (and the
        invoice still posts)."""
        template = self._template([self._item("freight_value")])
        move, line = self._draft_move(template)
        move.partner_id.property_account_receivable_id = False
        move.journal_id.default_account_id = False
        item = template.item_ids
        self.assertFalse(move._resolve_account(line, item, "debit"))
        self.assertEqual(move._prepare_double_entry_vals(line, item, set()), [])
        move.action_post()
        self.assertFalse(self._de_lines(move))

    def test_zero_or_done_fields_return_no_values(self):
        """Given a zero value field or an already done field, Then no values
        are prepared."""
        move, line = self._draft_move()
        item = self.sale_template.item_ids.filtered(
            lambda i: i.fiscal_field == "icms_value"
        )
        self.assertEqual(len(move._prepare_double_entry_vals(line, item, set())), 2)
        self.assertEqual(
            move._prepare_double_entry_vals(line, item, {"icms_value"}), []
        )
        line.icms_value = 0.0
        self.assertEqual(move._prepare_double_entry_vals(line, item, set()), [])

    def test_foreign_currency_move_converts_amount_currency(self):
        """Given an invoice in USD (company in BRL), Then the generated pair
        keeps the BRL balance and converts amount_currency to the document
        currency, so balance and amount_currency stay consistent."""
        usd = self.env.ref("base.USD")
        usd.active = True
        self.env["res.currency.rate"].create(
            {
                "name": "2019-01-01",
                "currency_id": usd.id,
                "company_id": self.company_data["company"].id,
                "rate": 0.25,
            }
        )
        move, line = self._draft_move()
        move.currency_id = usd
        item = self.sale_template.item_ids.filtered(
            lambda i: i.fiscal_field == "icms_value"
        )
        line.icms_value = 100.0
        debit_vals, credit_vals = move._prepare_double_entry_vals(line, item, set())
        self.assertEqual(debit_vals["balance"], 100.0)
        self.assertEqual(credit_vals["balance"], -100.0)
        self.assertAlmostEqual(debit_vals["amount_currency"], 25.0, places=2)
        self.assertAlmostEqual(credit_vals["amount_currency"], -25.0, places=2)
        self.assertEqual(debit_vals["currency_id"], usd.id)

    # ------------------------------------------------------------------
    # History text
    # ------------------------------------------------------------------
    def test_name_without_history_uses_label_and_line_name(self):
        """Given an item without standard history, Then the line text is the
        field label followed by the invoice line description."""
        move, line = self._draft_move()
        item = self.sale_template.item_ids.filtered(
            lambda i: i.fiscal_field == "icms_value"
        )
        name = move._prepare_double_entry_name(line, item, "ICMS próprio")
        self.assertEqual(name, "[ICMS próprio] %s" % (line.name or ""))

    # ------------------------------------------------------------------
    # Tax credit
    # ------------------------------------------------------------------
    def test_has_tax_credit_by_domain(self):
        """Given fiscal lines with different CSTs and credit flags, Then credit
        rights follow the documented rules per tax domain."""
        move = self.env["account.move"]
        line = SimpleNamespace(
            icms_cst_code="00",
            ipi_cst_code="02",
            pis_credit_id=self.env["l10n_br_fiscal.tax.pis.cofins"],
            cofins_credit_id=self.env["l10n_br_fiscal.tax.pis.cofins"],
        )
        for cst in ("00", "20", "60", "70"):
            line.icms_cst_code = cst
            self.assertTrue(move._has_tax_credit(line, "icms"), cst)
            self.assertTrue(move._has_tax_credit(line, "icmssn"), cst)
        line.icms_cst_code = "40"
        self.assertFalse(move._has_tax_credit(line, "icms"))
        self.assertFalse(move._has_tax_credit(line, "icmsst"))
        line.icms_cst_code = "60"
        self.assertTrue(move._has_tax_credit(line, "icmsst"))
        self.assertTrue(move._has_tax_credit(line, "ipi"))
        line.ipi_cst_code = "50"
        self.assertFalse(move._has_tax_credit(line, "ipi"))
        self.assertFalse(move._has_tax_credit(line, "pis"))
        self.assertFalse(move._has_tax_credit(line, "cofins"))
        line.pis_credit_id = SimpleNamespace()
        line.cofins_credit_id = SimpleNamespace()
        self.assertTrue(move._has_tax_credit(line, "pis"))
        self.assertTrue(move._has_tax_credit(line, "cofins"))
        # Domains without a rule never block the entry
        self.assertTrue(move._has_tax_credit(line, "issqn"))

    def test_require_tax_credit_only_filters_purchases(self):
        """Given an item requiring tax credit and a sale, Then the entry is
        still generated (the check is only for purchase operations)."""
        template = self._template(
            [
                self._item(
                    "icms_value",
                    self.account_icms_debit,
                    self.account_icms_credit,
                    require_tax_credit=True,
                    tax_domain="icms",
                )
            ]
        )
        move, line = self._draft_move(template)
        line.icms_cst_code = "40"
        move.action_post()
        self.assertEqual(len(self._de_lines(move)), 2)

    # ------------------------------------------------------------------
    # Template model
    # ------------------------------------------------------------------
    def test_item_onchange_fills_the_tax_domain(self):
        """Given an item, When the fiscal field changes, Then the tax domain
        follows the mapping; fields without mapping clear it."""
        item = self.env["l10n_br.account.move.template.item"].new(
            {"fiscal_field": "pis_wh_value"}
        )
        item._onchange_fiscal_field()
        self.assertEqual(item.tax_domain, "pis_wh")
        item.fiscal_field = "cbs_value"
        item._onchange_fiscal_field()
        self.assertEqual(item.tax_domain, "cbs")
        item.fiscal_field = "freight_value"
        item._onchange_fiscal_field()
        self.assertFalse(item.tax_domain)

    def test_parent_items_are_sorted_with_child_items(self):
        """Given a child with sequence 20 and a parent item with sequence 10,
        Then the merged items are ordered by sequence."""
        parent = self._template(
            [self._item("ipi_value", sequence=10)], name="Parent Seq"
        )
        child = self._template(
            [self._item("icms_value", sequence=20)],
            name="Child Seq",
            parent_id=parent.id,
        )
        self.assertEqual(
            child._get_all_items().mapped("fiscal_field"), ["ipi_value", "icms_value"]
        )

    def test_three_level_hierarchy_inherits_from_grandparent(self):
        """Given grandparent > parent > child, Then the child gets the items of
        all levels, the nearest one winning per field."""
        grand = self._template(
            [self._item("ipi_value", sequence=1), self._item("icms_value", sequence=2)],
            name="Grand",
        )
        parent = self._template(
            [self._item("icms_value", sequence=3)], name="Parent", parent_id=grand.id
        )
        child = self._template(
            [self._item("pis_value", sequence=4)], name="Child", parent_id=parent.id
        )
        items = child._get_all_items()
        self.assertEqual(
            sorted(items.mapped("fiscal_field")),
            ["icms_value", "ipi_value", "pis_value"],
        )
        self.assertEqual(
            items.filtered(lambda i: i.fiscal_field == "icms_value").template_id,
            parent,
        )

    @mute_logger("odoo.sql_db")
    def test_parent_template_with_children_cannot_be_deleted(self):
        """Given a parent with a child, When deleting the parent, Then it is
        refused (restrict); deleting a template removes its items."""
        parent = self._template([self._item("ipi_value")], name="P")
        self._template([], name="C", parent_id=parent.id)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            parent.unlink()
        standalone = self._template([self._item("ipi_value")], name="S")
        items = standalone.item_ids
        standalone.unlink()
        self.assertFalse(items.exists())

    def test_template_is_linked_per_fiscal_operation(self):
        """Given two fiscal operations, Then each one points to its own
        template and the sale operation's template drives the generation."""
        other = self.env.ref("l10n_br_fiscal.fo_compras")
        self.assertFalse(other.account_move_template_id)
        self.assertEqual(self.fo_sale.account_move_template_id, self.sale_template)

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    def test_templates_are_editable_by_account_managers_only(self):
        """Given an invoicing user and an account manager, Then the invoicing
        user only reads templates and the manager can write them."""
        invoicer = self.env["res.users"].create(
            {
                "name": "Invoicer",
                "login": "tpl_invoicer",
                "groups_id": [
                    (6, 0, [self.env.ref("account.group_account_invoice").id])
                ],
            }
        )
        manager = self.env["res.users"].create(
            {
                "name": "Manager",
                "login": "tpl_manager",
                "groups_id": [
                    (6, 0, [self.env.ref("account.group_account_manager").id])
                ],
            }
        )
        template = self.sale_template
        self.assertEqual(template.with_user(invoicer).name, "Sale Template")
        with self.assertRaises(AccessError):
            template.with_user(invoicer).write({"name": "Hacked"})
        with self.assertRaises(AccessError):
            template.item_ids.with_user(invoicer).write({"sequence": 99})
        template.with_user(manager).write({"name": "Renamed"})
        self.assertEqual(template.name, "Renamed")
