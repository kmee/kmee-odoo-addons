from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCustomerRating(TransactionCase):
    def test_image_rating_follows_rating(self):
        rating = self.env["customer.rating"].create(
            {"name": "Gold", "image": "iVBORw0KGgo="}
        )
        partner = self.env["res.partner"].create(
            {"name": "Rated Partner", "customer_rating_id": rating.id}
        )
        self.assertEqual(partner.image_rating, rating.image)
        partner.customer_rating_id = False
        self.assertFalse(partner.image_rating)
