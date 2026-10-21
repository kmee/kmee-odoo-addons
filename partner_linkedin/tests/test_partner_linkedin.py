# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerLinkedin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.url = "https://www.linkedin.com/in/fulano-de-tal"
        cls.Partner = cls.env["res.partner"]

    def test_partner_without_linkedin_has_empty_field(self):
        """Given a new partner without informing the profile
        When it is created
        Then linkedin_url is empty (no default value)."""
        partner = self.Partner.create({"name": "No LinkedIn"})
        self.assertFalse(partner.linkedin_url)

    def test_linkedin_url_is_stored_on_create(self):
        """Given a partner created with a LinkedIn URL
        When the record is read back from the database
        Then the URL is persisted unchanged."""
        partner = self.Partner.create(
            {"name": "With LinkedIn", "linkedin_url": self.url}
        )
        partner.invalidate_recordset()
        self.assertEqual(partner.linkedin_url, self.url)

    def test_linkedin_url_can_be_updated_and_cleared(self):
        """Given a partner with a profile
        When the URL is changed and then cleared
        Then the field follows each write."""
        partner = self.Partner.create({"name": "Edit", "linkedin_url": self.url})
        partner.linkedin_url = self.url + "-2"
        self.assertTrue(partner.linkedin_url.endswith("-2"))
        partner.linkedin_url = False
        self.assertFalse(partner.linkedin_url)

    def test_search_by_linkedin_url(self):
        """Given two partners, one with the profile
        When searching by linkedin_url
        Then only the partner with the profile is found."""
        with_url = self.Partner.create({"name": "Has", "linkedin_url": self.url})
        without = self.Partner.create({"name": "Hasnt"})
        found = self.Partner.search([("linkedin_url", "=", self.url)])
        self.assertIn(with_url, found)
        self.assertNotIn(without, found)

    def test_form_view_edits_linkedin_url(self):
        """Given the partner form view
        When the user fills the LinkedIn field in the form
        Then the value is saved in the record."""
        # 19.0: Form needs onchange(), which lives in the web module
        if not self.env["ir.module.module"].search_count(
            [("name", "=", "web"), ("state", "=", "installed")]
        ):
            self.skipTest("web is not installed")
        form = Form(self.Partner)
        form.name = "Form partner"
        form.linkedin_url = self.url
        partner = form.save()
        self.assertEqual(partner.linkedin_url, self.url)

    def test_form_view_places_field_after_website_with_url_widget(self):
        """Given the res.partner form view
        When its architecture is computed
        Then linkedin_url is shown right after website using the url widget."""
        arch = self.Partner.get_view(self.env.ref("base.view_partner_form").id)["arch"]
        tree = etree.fromstring(arch)
        names = [f.get("name") for f in tree.iter("field")]
        self.assertIn("linkedin_url", names)
        self.assertEqual(names[names.index("website") + 1], "linkedin_url")
        node = tree.xpath("//field[@name='linkedin_url']")[0]
        self.assertEqual(node.get("widget"), "url")
