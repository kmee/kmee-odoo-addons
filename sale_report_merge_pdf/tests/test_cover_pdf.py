# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import new_test_user, tagged
from odoo.tools import mute_logger

from .common import CoverPdfCase


@tagged("post_install", "-at_install")
class TestCoverPdf(CoverPdfCase):
    def test_only_one_active_cover_on_create(self):
        """
        Given an active cover
        When another active cover is created
        Then a ValidationError blocks it and only the first remains
        """
        first = self.make_cover()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.make_cover()
        self.assertEqual(self.Cover.search([]), first)

    def test_batch_create_of_two_active_covers_is_blocked(self):
        """
        Given no cover
        When two active covers are created in the same call
        Then the constraint refuses the batch
        """
        values = {"cover_pdf_filename": "x.pdf"}
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.Cover.create([dict(values), dict(values)])
        self.assertFalse(self.Cover.search([]))

    def test_archiving_several_covers_at_once(self):
        """
        Given two archived covers
        When both are written in one call
        Then no error is raised (the check must work on multi-record sets)
        """
        covers = self.make_cover(active=False) | self.make_cover(active=False)
        covers.write({"active": False, "cover_pdf_filename": "old.pdf"})
        self.assertEqual(covers.mapped("cover_pdf_filename"), ["old.pdf", "old.pdf"])

    def test_inactive_cover_can_coexist(self):
        """
        Given an active cover
        When an archived cover is created
        Then it is accepted, and the active one is still the one returned
        """
        first = self.make_cover()
        archived = self.make_cover(active=False)
        self.assertFalse(archived.active)
        self.assertEqual(self.Cover.get_active_cover(), first)

    def test_reactivating_second_cover_is_blocked(self):
        """
        Given an active cover and an archived one
        When the archived one is reactivated
        Then the constraint refuses it
        """
        self.make_cover()
        archived = self.make_cover(active=False)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            archived.active = True
        self.assertFalse(archived.active)

    def test_swap_cover_after_archiving_the_current_one(self):
        """
        Given an active cover
        When it is archived and a new one is created
        Then the new one becomes the active cover
        """
        first = self.make_cover()
        first.active = False
        second = self.make_cover(cover_pdf_filename="new.pdf")
        self.assertEqual(self.Cover.get_active_cover(), second)

    def test_get_active_cover_needs_a_pdf_file(self):
        """
        Given no cover, then a cover record without file, then one with file
        When the active cover is requested
        Then only the record that holds a PDF is returned
        """
        self.assertFalse(self.Cover.get_active_cover())
        empty = self.Cover.create({"cover_pdf_filename": "empty.pdf"})
        self.assertFalse(self.Cover.get_active_cover())
        empty.cover_pdf = self.make_cover(active=False).cover_pdf
        self.assertEqual(self.Cover.get_active_cover(), empty)

    def test_display_name_has_default(self):
        """
        Given a cover created without a name
        When its name is read
        Then the default name is set
        """
        self.assertTrue(self.make_cover().display_name)

    def test_salesman_can_read_but_not_change_covers(self):
        """
        Given a salesman without manager rights
        When he reads, writes, creates and deletes covers
        Then only reading works
        """
        cover = self.make_cover()
        salesman = new_test_user(
            self.env, login="cover_salesman", groups="sales_team.group_sale_salesman"
        )
        as_salesman = cover.with_user(salesman)
        self.assertEqual(as_salesman.cover_pdf_filename, "cover.pdf")
        with self.assertRaises(AccessError):
            as_salesman.write({"cover_pdf_filename": "x.pdf"})
        with self.assertRaises(AccessError):
            self.Cover.with_user(salesman).create({"active": False})
        with self.assertRaises(AccessError):
            as_salesman.unlink()

    def test_sales_manager_can_manage_covers(self):
        """
        Given a sales manager
        When he edits and deletes the cover
        Then both operations succeed
        """
        cover = self.make_cover()
        manager = new_test_user(
            self.env, login="cover_manager", groups="sales_team.group_sale_manager"
        )
        cover.with_user(manager).write({"cover_pdf_filename": "x.pdf"})
        self.assertEqual(cover.cover_pdf_filename, "x.pdf")
        with mute_logger("odoo.models.unlink"):
            cover.with_user(manager).unlink()
        self.assertFalse(cover.exists())
