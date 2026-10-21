from odoo.exceptions import AccessError
from odoo.tests import Form, TransactionCase, tagged
from odoo.tools import mute_logger

ICON_A = "iVBORw0KGgo="
ICON_B = "R0lGODlhAQABAAAAACw="


@tagged("post_install", "-at_install")
class TestCustomerRating(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Rating = cls.env["customer.rating"]
        cls.Partner = cls.env["res.partner"]
        cls.rating = cls.Rating.create({"name": "Gold", "image": ICON_A})
        cls.user = cls.env["res.users"].create(
            {
                "name": "Plain User",
                "login": "rating_plain_user",
                "email": "rating_plain_user@example.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def test_image_rating_follows_rating(self):
        """Given a rating with an icon, When a partner gets that rating,
        Then image_rating mirrors the icon; clearing the rating clears it."""
        partner = self.Partner.create(
            {"name": "Rated Partner", "customer_rating_id": self.rating.id}
        )
        self.assertEqual(partner.image_rating.to_base64(), ICON_A)
        partner.customer_rating_id = False
        self.assertFalse(partner.image_rating)

    def test_image_rating_recomputed_when_rating_icon_changes(self):
        """Given a rated partner, When the rating icon changes,
        Then the partner icon is recomputed."""
        partner = self.Partner.create(
            {"name": "Rated Partner", "customer_rating_id": self.rating.id}
        )
        self.rating.image = ICON_B
        self.assertEqual(partner.image_rating.to_base64(), ICON_B)
        self.assertNotEqual(partner.image_rating.to_base64(), ICON_A)

    def test_image_rating_when_switching_rating(self):
        """Given two ratings, When the partner switches, Then the icon switches."""
        other = self.Rating.create({"name": "Bronze", "image": ICON_B})
        partner = self.Partner.create(
            {"name": "Switcher", "customer_rating_id": self.rating.id}
        )
        partner.customer_rating_id = other
        self.assertEqual(partner.image_rating.to_base64(), ICON_B)

    def test_rating_without_icon(self):
        """Given a rating without icon, Then the partner icon is empty."""
        bare = self.Rating.create({"name": "No icon"})
        partner = self.Partner.create({"name": "Bare", "customer_rating_id": bare.id})
        self.assertFalse(partner.image_rating)

    def test_search_customer_rating_helper(self):
        """Given ratings, When searching by name, Then the domain targets only
        partners with matching ratings."""
        other = self.Rating.create({"name": "Bronze", "image": ICON_B})
        p_gold = self.Partner.create(
            {"name": "P gold", "customer_rating_id": self.rating.id}
        )
        p_bronze = self.Partner.create(
            {"name": "P bronze", "customer_rating_id": other.id}
        )
        domain = self.Partner._search_customer_rating("ilike", "gold")
        found = self.Partner.search(domain)
        self.assertIn(p_gold, found)
        self.assertNotIn(p_bronze, found)

    def test_group_by_rating(self):
        """Given rated partners, When grouping by rating, Then each group counts."""
        self.Partner.create({"name": "A", "customer_rating_id": self.rating.id})
        self.Partner.create({"name": "B", "customer_rating_id": self.rating.id})
        groups = self.Partner._read_group(
            [("customer_rating_id", "=", self.rating.id)],
            ["customer_rating_id"],
            ["__count"],
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0][1], 2)

    def test_rating_field_is_tracked(self):
        """Given the partner chatter, Then the rating is a tracked field, so
        changes to it are logged by the mail machinery."""
        self.assertIn("customer_rating_id", self.Partner._track_get_fields())
        self.assertTrue(self.Partner._fields["customer_rating_id"].tracking)

    # 19.0: with the whole repository installed, another module warns that its
    # partner_id child_of domain gets the NewId of the form record
    @mute_logger("odoo.domains")
    def test_form_sets_rating(self):
        """Given the partner form, When selecting a rating, Then it is saved."""
        form = Form(self.Partner)
        form.name = "Form partner"
        form.customer_rating_id = self.rating
        partner = form.save()
        self.assertEqual(partner.customer_rating_id, self.rating)
        self.assertEqual(partner.image_rating.to_base64(), ICON_A)

    def test_internal_user_can_read_but_not_write_rating(self):
        """Given an internal user, Then reading ratings works but writing and
        creating are denied by ACL."""
        rating = self.rating.with_user(self.user)
        self.assertEqual(rating.name, "Gold")
        with self.assertRaises(AccessError):
            rating.write({"name": "Hacked"})
        with self.assertRaises(AccessError):
            self.Rating.with_user(self.user).create({"name": "New"})
        with self.assertRaises(AccessError):
            rating.unlink()

    def test_system_admin_can_manage_ratings(self):
        """Given a settings admin, Then CRUD on ratings is allowed."""
        admin = self.env.ref("base.user_admin")
        new = self.Rating.with_user(admin).create({"name": "Platinum"})
        new.write({"name": "Platinum+"})
        self.assertEqual(new.name, "Platinum+")
        new.unlink()
        self.assertFalse(new.exists())

    def test_deleting_rating_clears_partner(self):
        """Given a rated partner, When the rating is deleted, Then the partner
        stays and has no rating."""
        other = self.Rating.create({"name": "Temp", "image": ICON_B})
        partner = self.Partner.create(
            {"name": "Orphan", "customer_rating_id": other.id}
        )
        other.unlink()
        self.assertFalse(partner.customer_rating_id)
        self.assertFalse(partner.image_rating)
