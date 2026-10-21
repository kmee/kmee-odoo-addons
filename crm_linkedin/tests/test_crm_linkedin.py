# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests.common import Form, TransactionCase, tagged

URL_A = "https://www.linkedin.com/in/ana-example"
URL_B = "https://www.linkedin.com/in/bruno-example"


@tagged("post_install", "-at_install")
class TestCrmLinkedin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Lead = cls.env["crm.lead"]
        cls.partner_with = cls.env["res.partner"].create(
            {"name": "Ana", "linkedin_url": URL_A}
        )
        cls.partner_without = cls.env["res.partner"].create({"name": "Bruno"})

    def _lead(self, **vals):
        vals.setdefault("name", "LinkedIn lead")
        return self.Lead.create(vals)

    # partner -> lead -------------------------------------------------------

    def test_lead_takes_linkedin_from_partner_on_create(self):
        """Given a partner with a profile, a lead created for it shows that profile."""
        lead = self._lead(partner_id=self.partner_with.id)
        self.assertEqual(lead.linkedin_url, URL_A)

    def test_lead_without_partner_has_no_profile(self):
        """Given a lead without partner, the profile is empty."""
        self.assertFalse(self._lead().linkedin_url)

    def test_lead_with_partner_without_profile_has_none(self):
        """Given a partner with no profile, the lead has none."""
        lead = self._lead(partner_id=self.partner_without.id)
        self.assertFalse(lead.linkedin_url)

    def test_lead_follows_partner_profile_change(self):
        """Given a linked lead, when the partner profile changes, the lead follows."""
        lead = self._lead(partner_id=self.partner_with.id)
        self.partner_with.linkedin_url = URL_B
        self.assertEqual(lead.linkedin_url, URL_B)

    def test_lead_updates_when_partner_is_replaced(self):
        """Given a lead, when its partner changes, the profile is taken from the new one."""
        lead = self._lead(partner_id=self.partner_without.id)
        lead.partner_id = self.partner_with
        self.assertEqual(lead.linkedin_url, URL_A)

    def test_lead_clears_profile_when_partner_profile_is_removed(self):
        """Given a linked lead, when the partner profile is erased, the lead
        does not keep the old URL."""
        lead = self._lead(partner_id=self.partner_with.id)
        self.partner_with.linkedin_url = False
        self.assertFalse(lead.linkedin_url)

    def test_lead_clears_profile_when_partner_without_profile_is_chosen(self):
        """Given a lead of a partner with a profile, when the partner is replaced
        by one without profile, the old URL (of another person) is dropped and
        the new partner is not touched."""
        lead = self._lead(partner_id=self.partner_with.id)
        lead.partner_id = self.partner_without
        self.assertFalse(lead.linkedin_url)
        self.assertFalse(self.partner_without.linkedin_url)
        self.assertEqual(self.partner_with.linkedin_url, URL_A)

    def test_lead_clears_profile_when_partner_is_removed(self):
        """Given a linked lead, when the partner is removed from it or deleted,
        the URL that came from the partner goes away too."""
        lead = self._lead(partner_id=self.partner_with.id)
        lead.partner_id = False
        self.assertFalse(lead.linkedin_url)
        other = self.env["res.partner"].create({"name": "Gone", "linkedin_url": URL_B})
        lead_of_other = self._lead(partner_id=other.id)
        other.unlink()
        self.assertFalse(lead_of_other.partner_id)
        self.assertFalse(lead_of_other.linkedin_url)

    def test_form_clears_profile_when_partner_changes(self):
        """Given the form, switching to a partner without profile clears it."""
        form = Form(self.Lead.with_context(default_type="opportunity"))
        form.name = "Form switch"
        form.partner_id = self.partner_with
        self.assertEqual(form.linkedin_url, URL_A)
        form.partner_id = self.partner_without
        self.assertFalse(form.linkedin_url)
        lead = form.save()
        self.assertFalse(lead.linkedin_url)
        self.assertEqual(self.partner_with.linkedin_url, URL_A)

    # lead -> partner -------------------------------------------------------

    def test_editing_lead_profile_updates_partner(self):
        """Given a linked lead, when the profile is edited, the partner is updated."""
        lead = self._lead(partner_id=self.partner_without.id)
        lead.linkedin_url = URL_B
        self.assertEqual(self.partner_without.linkedin_url, URL_B)
        self.assertEqual(lead.linkedin_url, URL_B)

    def test_lead_without_partner_keeps_own_profile(self):
        """Given a lead without partner, the profile is stored on the lead only."""
        lead = self._lead(linkedin_url=URL_A)
        self.assertEqual(lead.linkedin_url, URL_A)
        self.assertFalse(self.partner_without.linkedin_url)

    def test_two_leads_of_a_partner_share_its_profile(self):
        """Given two leads of one partner, editing one propagates to the other."""
        first = self._lead(partner_id=self.partner_without.id, name="First")
        second = self._lead(partner_id=self.partner_without.id, name="Second")
        first.linkedin_url = URL_B
        self.assertEqual(second.linkedin_url, URL_B)

    # lead -> new customer ------------------------------------------------

    def test_new_customer_gets_the_lead_profile(self):
        """Given a lead with a profile and no partner, the created customer keeps it."""
        lead = self._lead(
            partner_name="Acme Ltd",
            contact_name="Carla Contact",
            linkedin_url=URL_B,
        )
        lead._handle_partner_assignment(create_missing=True)
        self.assertTrue(lead.partner_id)
        self.assertEqual(lead.partner_id.linkedin_url, URL_B)
        self.assertEqual(lead.linkedin_url, URL_B)

    def test_new_customer_without_profile_stays_clean(self):
        """Given a lead without profile, the created customer has none."""
        lead = self._lead(partner_name="Acme 2", contact_name="Dani Contact")
        lead._handle_partner_assignment(create_missing=True)
        self.assertTrue(lead.partner_id)
        self.assertFalse(lead.partner_id.linkedin_url)

    def test_prepare_customer_values_carries_profile(self):
        """Given a lead with a profile, the customer values include it."""
        lead = self._lead(linkedin_url=URL_A)
        values = lead._prepare_customer_values("Someone")
        self.assertEqual(values["linkedin_url"], URL_A)
        self.assertEqual(values["name"], "Someone")
        plain = self._lead(name="Plain")._prepare_customer_values("Someone")
        self.assertNotIn("linkedin_url", plain)

    # views -----------------------------------------------------------------

    def test_form_shows_profile_after_job_position(self):
        """Given the lead form, the profile field follows the job position field."""
        arch = etree.fromstring(
            self.Lead.get_view(self.env.ref("crm.crm_lead_view_form").id)["arch"]
        )
        fields = arch.xpath("//field[@name='linkedin_url']")
        self.assertTrue(fields)
        self.assertTrue(all(f.get("widget") == "url" for f in fields))
        self.assertTrue(all(f.getprevious().get("name") == "function" for f in fields))

    def test_form_fills_profile_from_chosen_partner_and_saves_edit(self):
        """Given the form, picking a partner fills the profile, and edits reach the partner."""
        form = Form(self.Lead.with_context(default_type="opportunity"))
        form.name = "Form LinkedIn"
        form.partner_id = self.partner_with
        self.assertEqual(form.linkedin_url, URL_A)
        form.linkedin_url = URL_B
        lead = form.save()
        self.assertEqual(lead.linkedin_url, URL_B)
        self.assertEqual(self.partner_with.linkedin_url, URL_B)
