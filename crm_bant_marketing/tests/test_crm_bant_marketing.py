# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests.common import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCrmBantMarketing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Lead = cls.env["crm.lead"].with_context(tracking_disable=True)
        cls.campaign = cls.env["utm.campaign"].create({"name": "BANT campaign"})
        cls.medium = cls.env["utm.medium"].create({"name": "BANT medium"})
        cls.source = cls.env["utm.source"].create({"name": "BANT source"})

    def _arch(self):
        view = self.env.ref("crm.crm_lead_view_form")
        return etree.fromstring(self.Lead.get_view(view.id)["arch"])

    def test_marketing_group_sits_inside_the_bant_page(self):
        """Given the lead form, the Marketing group is in the BANT page after status."""
        arch = self._arch()
        group = arch.xpath(
            "//page[@name='bant_qualification']//group[@string='Marketing']"
        )
        self.assertEqual(len(group), 1)
        fields = group[0].xpath("./field/@name")
        self.assertEqual(fields, ["campaign_id", "medium_id", "source_id", "referred"])
        # placed right after the BANT status group
        previous = group[0].getprevious()
        self.assertEqual(previous.get("name"), "bant_status")

    def test_view_extends_the_bant_form_not_the_core_form_directly(self):
        """Given the inherited view, it is a child of the crm_bant form."""
        view = self.env.ref(
            "crm_bant_marketing.crm_case_form_view_oppor_bant_marketing"
        )
        self.assertEqual(
            view.inherit_id, self.env.ref("crm_bant.crm_case_form_view_oppor_bant")
        )

    def test_form_saves_marketing_fields_from_bant_page(self):
        """Given the form, when marketing fields are filled, they persist on the lead."""
        form = Form(self.Lead.with_context(default_type="opportunity"))
        form.name = "Marketing BANT"
        form.campaign_id = self.campaign
        form.medium_id = self.medium
        form.source_id = self.source
        form.referred = "Partner referral"
        lead = form.save()
        self.assertEqual(lead.campaign_id, self.campaign)
        self.assertEqual(lead.medium_id, self.medium)
        self.assertEqual(lead.source_id, self.source)
        self.assertEqual(lead.referred, "Partner referral")

    def test_marketing_fields_do_not_affect_bant_score(self):
        """Given marketing data, the BANT score still depends only on BANT statuses."""
        lead = self.Lead.create(
            {
                "name": "Marketing only",
                "type": "opportunity",
                "campaign_id": self.campaign.id,
                "source_id": self.source.id,
            }
        )
        self.assertEqual(lead.bant_total_score, 0)
        lead.bant_budget_status = "budget_approved"
        self.assertEqual(lead.bant_total_score, 3)
        self.assertEqual(lead.campaign_id, self.campaign)
