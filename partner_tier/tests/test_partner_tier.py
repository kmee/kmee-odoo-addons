from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerTier(TransactionCase):
    def test_partner_count_and_action(self):
        tier = self.env["res.partner.tier"].create({"name": "Gold"})
        self.assertEqual(tier.partner_count, 0)
        self.env["res.partner"].create({"name": "Tiered", "tier_id": tier.id})
        tier.invalidate_recordset()
        self.assertEqual(tier.partner_count, 1)
        action = tier.action_view_partners()
        self.assertEqual(action["domain"], [("tier_id", "=", tier.id)])

    def test_tier_is_commercial_field(self):
        self.assertIn("tier_id", self.env["res.partner"]._commercial_fields())
