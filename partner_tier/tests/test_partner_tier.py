from odoo.exceptions import AccessError
from odoo.tests import Form, TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestPartnerTier(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Tier = cls.env["res.partner.tier"]
        cls.Partner = cls.env["res.partner"]
        cls.gold = cls.Tier.create({"name": "Gold Test", "sequence": 1})
        cls.silver = cls.Tier.create({"name": "Silver Test", "sequence": 2})
        group_user = cls.env.ref("base.group_user")
        cls.user = cls.env["res.users"].create(
            {
                "name": "Tier User",
                "login": "tier_plain_user",
                "email": "tier_plain_user@example.com",
                "group_ids": [(6, 0, [group_user.id])],
            }
        )
        cls.manager = cls.env["res.users"].create(
            {
                "name": "Tier Manager",
                "login": "tier_manager",
                "email": "tier_manager@example.com",
                "group_ids": [
                    (
                        6,
                        0,
                        [group_user.id, cls.env.ref("base.group_partner_manager").id],
                    )
                ],
            }
        )

    def test_defaults(self):
        """Given a new tier, Then it defaults to sequence 10 and medium priority."""
        tier = self.Tier.create({"name": "Defaults"})
        self.assertEqual(tier.sequence, 10)
        self.assertEqual(tier.priority, "1")
        self.assertEqual(tier.partner_count, 0)

    def test_tiers_ordered_by_sequence(self):
        """Given tiers with sequences, When searching, Then lowest sequence first."""
        found = self.Tier.search([("id", "in", (self.gold | self.silver).ids)])
        self.assertEqual(found.ids, [self.gold.id, self.silver.id])
        self.silver.sequence = 0
        found = self.Tier.search([("id", "in", (self.gold | self.silver).ids)])
        self.assertEqual(found.ids, [self.silver.id, self.gold.id])

    def test_partner_count_and_action(self):
        """Given partners with a tier, Then partner_count counts only them and
        the action domain targets that tier."""
        self.Partner.create({"name": "T1", "tier_id": self.gold.id})
        self.Partner.create({"name": "T2", "tier_id": self.gold.id})
        self.Partner.create({"name": "T3", "tier_id": self.silver.id})
        self.assertEqual(self.gold.partner_count, 2)
        self.assertEqual(self.silver.partner_count, 1)
        action = self.gold.action_view_partners()
        self.assertEqual(action["res_model"], "res.partner")
        self.assertEqual(action["domain"], [("tier_id", "=", self.gold.id)])
        self.assertEqual(len(self.Partner.search(action["domain"])), 2)

    def test_action_view_partners_requires_single_record(self):
        """Given two tiers, When opening partners, Then ensure_one rejects it."""
        with self.assertRaises(ValueError):
            (self.gold | self.silver).action_view_partners()

    def test_tier_is_commercial_field(self):
        """Then tier_id is listed among the commercial fields."""
        self.assertIn("tier_id", self.Partner._commercial_fields())

    def test_tier_propagates_to_contacts_on_create(self):
        """Given a company with a tier, When a contact is created under it,
        Then the contact inherits the tier."""
        company = self.Partner.create(
            {"name": "Co", "is_company": True, "tier_id": self.gold.id}
        )
        contact = self.Partner.create({"name": "Person", "parent_id": company.id})
        self.assertEqual(contact.tier_id, self.gold)

    def test_tier_propagates_to_contacts_on_write(self):
        """Given a company with contacts, When its tier changes, Then the
        contacts follow."""
        company = self.Partner.create(
            {"name": "Co", "is_company": True, "tier_id": self.gold.id}
        )
        contact = self.Partner.create({"name": "Person", "parent_id": company.id})
        company.tier_id = self.silver
        self.assertEqual(contact.tier_id, self.silver)

    # 19.0: with the whole repository installed, another module warns that its
    # partner_id child_of domain gets the NewId of the form record
    @mute_logger("odoo.domains")
    def test_form_tier_readonly_for_contact_of_company(self):
        """Given a contact with a parent, Then the form makes the tier read-only
        (it comes from the company); a standalone partner can edit it."""
        company = self.Partner.create(
            {"name": "Co", "is_company": True, "tier_id": self.gold.id}
        )
        contact = self.Partner.create({"name": "Person", "parent_id": company.id})
        with Form(contact) as form:
            with self.assertRaises(AssertionError):
                form.tier_id = self.silver
        form = Form(self.Partner)
        form.name = "Standalone"
        form.tier_id = self.silver
        self.assertEqual(form.save().tier_id, self.silver)

    def test_group_by_tier(self):
        """Given partners in tiers, When grouping by tier, Then counts match."""
        self.Partner.create({"name": "T1", "tier_id": self.gold.id})
        self.Partner.create({"name": "T2", "tier_id": self.gold.id})
        groups = self.Partner._read_group(
            [("tier_id", "=", self.gold.id)], ["tier_id"], ["__count"]
        )
        self.assertEqual(groups[0][1], 2)

    def test_internal_user_reads_but_cannot_edit_tiers(self):
        """Given a plain internal user, Then tiers are readable only."""
        tier = self.gold.with_user(self.user)
        self.assertEqual(tier.name, "Gold Test")
        with self.assertRaises(AccessError):
            tier.write({"name": "X"})
        with self.assertRaises(AccessError):
            self.Tier.with_user(self.user).create({"name": "New"})

    def test_partner_manager_manages_tiers(self):
        """Given a partner manager, Then CRUD on tiers is allowed."""
        tier = self.Tier.with_user(self.manager).create({"name": "Mgr tier"})
        tier.write({"priority": "3"})
        self.assertEqual(tier.priority, "3")
        tier.unlink()
        self.assertFalse(tier.exists())

    def test_demo_tiers_loaded(self):
        """Demo tiers exist with the expected ordering (gold first)."""
        gold = self.env.ref("partner_tier.partner_tier_gold", raise_if_not_found=False)
        bronze = self.env.ref(
            "partner_tier.partner_tier_bronze", raise_if_not_found=False
        )
        if not gold or not bronze:
            self.skipTest("demo data not loaded")
        self.assertLess(gold.sequence, bronze.sequence)
