# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

# The Brazilian fiscal fields come from l10n_br_stock_account, which is not a
# dependency of this module. They are emulated on stock.move during the call
# so that the Brazilian branches of ``_get_price_unit`` can be exercised.
FISCAL_FIELDS = (
    "fiscal_operation_id",
    "amount_taxed",
    "amount_untaxed",
    "amount_tax_included",
)


@tagged("post_install", "-at_install")
class TestCategoryCostControl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.categ = cls.env["product.category"].create({"name": "Cost control categ"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Cost control product",
                "type": "product",
                "categ_id": cls.categ.id,
            }
        )
        warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.move = cls.env["stock.move"].create(
            {
                "name": "Receipt",
                "product_id": cls.product.id,
                "product_uom_qty": 10.0,
                "product_uom": cls.product.uom_id.id,
                "price_unit": 7.0,
                "location_id": cls.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": warehouse.lot_stock_id.id,
            }
        )

    @contextmanager
    def _fiscal(self, op_type="in", present=FISCAL_FIELDS, **amounts):
        """Emulate the l10n_br_stock_account fields on stock.move.

        Only the names in ``present`` exist in ``_fields`` inside the block, even
        when l10n_br_stock_account is installed (full CI suite)."""
        cls = type(self.move)
        operation = SimpleNamespace(fiscal_operation_type=op_type) if op_type else False
        values = {"fiscal_operation_id": operation, **amounts}
        fake = {}
        for name in present:
            fake[name] = fields.Float(store=False)
            fake[name].name = name
            fake[name].store = False
            fake[name].prefetch = False
        with ExitStack() as stack:
            stack.enter_context(patch.dict(cls._fields))
            for name in FISCAL_FIELDS:
                cls._fields.pop(name, None)
            cls._fields.update(fake)
            for name, value in values.items():
                stack.enter_context(
                    patch.object(
                        cls,
                        name,
                        new_callable=PropertyMock,
                        return_value=value,
                        create=True,
                    )
                )
            yield

    def _baseline(self):
        return super(type(self.move), self.move)._get_price_unit()

    def test_category_option_selection_values(self):
        """Given a category, When choosing the cost option, Then only the two
        documented options are accepted and the default is empty."""
        self.assertFalse(self.categ.price_control_option)
        self.categ.price_control_option = "include_all_taxes"
        self.categ.price_control_option = "remove_included_taxes"
        with self.assertRaises(ValueError):
            self.categ.price_control_option = "something_else"

    def test_non_brazilian_move_keeps_standard_price_unit(self):
        """Given a category with an option but no fiscal operation field on
        the move, When computing the price unit, Then the core value is kept."""
        self.categ.price_control_option = "include_all_taxes"
        with self._fiscal(present=(), amount_taxed=120.0):
            self.assertNotIn("fiscal_operation_id", self.move._fields)
            self.assertEqual(self.move._get_price_unit(), 7.0)
            self.assertEqual(self.move._get_price_unit(), self._baseline())

    def test_include_all_taxes_uses_amount_taxed_per_unit(self):
        """Given an inbound fiscal move and include_all_taxes, When computing
        the price unit, Then it is amount_taxed / quantity (taxes included)."""
        self.categ.price_control_option = "include_all_taxes"
        with self._fiscal(amount_taxed=120.0):
            self.assertAlmostEqual(self.move._get_price_unit(), 12.0)
        self.assertEqual(self.move._get_price_unit(), 7.0)

    def test_remove_included_taxes_discounts_recoverable_taxes(self):
        """Given remove_included_taxes, When computing the price unit, Then it
        is (untaxed - tax included) / quantity."""
        self.categ.price_control_option = "remove_included_taxes"
        with self._fiscal(amount_untaxed=100.0, amount_tax_included=18.5):
            self.assertAlmostEqual(self.move._get_price_unit(), 8.15)

    def test_no_option_on_category_keeps_core_value(self):
        """Given a Brazilian inbound move and a category without option, Then
        the core price unit is untouched."""
        with self._fiscal(amount_taxed=120.0):
            self.assertEqual(self.move._get_price_unit(), 7.0)

    def test_outbound_operation_is_ignored(self):
        """Given an outbound fiscal operation, Then the category option does
        not change the price unit."""
        self.categ.price_control_option = "include_all_taxes"
        with self._fiscal(op_type="out", amount_taxed=120.0):
            self.assertEqual(self.move._get_price_unit(), 7.0)

    def test_move_without_fiscal_operation_is_ignored(self):
        """Given a move whose fiscal operation is empty, Then the core value
        is kept."""
        self.categ.price_control_option = "include_all_taxes"
        with self._fiscal(op_type=False, amount_taxed=120.0):
            self.assertEqual(self.move._get_price_unit(), 7.0)

    def test_missing_amount_fields_fall_back_to_core(self):
        """Given the fiscal operation but no amount fields on the move, Then
        neither option breaks and the core value is kept."""
        self.categ.price_control_option = "include_all_taxes"
        with self._fiscal(present=("fiscal_operation_id",)):
            self.assertEqual(self.move._get_price_unit(), 7.0)
        self.categ.price_control_option = "remove_included_taxes"
        with self._fiscal(
            present=("fiscal_operation_id", "amount_untaxed"), amount_untaxed=100.0
        ):
            self.assertEqual(self.move._get_price_unit(), 7.0)

    def test_quantity_done_has_precedence_over_demand(self):
        """Given a move with 10 demanded and 4 done, When computing, Then the
        unit price divides by the done quantity."""
        self.categ.price_control_option = "include_all_taxes"
        self.move._action_confirm()
        self.move.quantity_done = 4.0
        with self._fiscal(amount_taxed=120.0):
            self.assertAlmostEqual(self.move._get_price_unit(), 30.0)

    def test_zero_quantity_does_not_divide_by_zero(self):
        """Given a move with no quantity at all, Then the core value is
        returned instead of a ZeroDivisionError."""
        self.categ.price_control_option = "include_all_taxes"
        self.move.product_uom_qty = 0.0
        with self._fiscal(amount_taxed=120.0):
            self.assertEqual(self.move._get_price_unit(), self._baseline())

    def test_product_without_category_option_follows_its_own_category(self):
        """Given two categories, When moving products of each, Then only the
        one configured changes the price unit."""
        other = self.env["product.category"].create({"name": "Other"})
        self.categ.price_control_option = "include_all_taxes"
        self.product.categ_id = other
        with self._fiscal(amount_taxed=120.0):
            self.assertEqual(self.move._get_price_unit(), 7.0)
        self.product.categ_id = self.categ
        with self._fiscal(amount_taxed=120.0):
            self.assertAlmostEqual(self.move._get_price_unit(), 12.0)

    def test_form_field_visible_only_to_accounting_or_stock_manager(self):
        """Given the category form, When a plain employee loads it, Then the
        option is hidden; a stock manager sees it."""
        employee = self.env["res.users"].create(
            {
                "name": "Employee",
                "login": "cost_employee",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        accountant = self.env["res.users"].create(
            {
                "name": "Accountant",
                "login": "cost_accountant",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("account.group_account_readonly").id,
                        ],
                    )
                ],
            }
        )
        manager = self.env["res.users"].create(
            {
                "name": "Stock manager",
                "login": "cost_manager",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("stock.group_stock_manager").id,
                        ],
                    )
                ],
            }
        )
        self.assertTrue(manager.has_group("stock.group_stock_manager"))
        self.assertFalse(employee.has_group("stock.group_stock_manager"))
        Categ = self.env["product.category"]
        arch_employee = Categ.with_user(employee).get_view(view_type="form")["arch"]
        arch_manager = Categ.with_user(manager).get_view(view_type="form")["arch"]
        arch_accountant = Categ.with_user(accountant).get_view(view_type="form")["arch"]
        self.assertNotIn("price_control_option", arch_employee)
        self.assertIn("price_control_option", arch_accountant)
        self.assertIn("price_control_option", arch_manager)

    def test_employee_cannot_change_category_option(self):
        """Given a plain employee, When writing the option, Then access is
        denied by the core category ACL."""
        employee = self.env["res.users"].create(
            {
                "name": "Employee 2",
                "login": "cost_employee2",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self.categ.with_user(employee).price_control_option = "include_all_taxes"
