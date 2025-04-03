from odoo.tests.common import BaseCommon


class TestSac(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sac_model = cls.env["sac"]
        cls.reason_model = cls.env["sac.reason"]
        cls.type_model = cls.env["sac.type"]

    def test_create_sac(self):
        """Test SAC creation"""
        sac = self.sac_model.create(
            {
                "customer_name": "Test Customer",
                "email_from": "test@example.com",
                "phone": "1234567890",
            }
        )
        self.assertTrue(sac.name.startswith("New"))
        self.assertEqual(sac.customer_name, "Test Customer")

    def test_compute_display_name(self):
        """Test display name computation"""
        sac = self.sac_model.create(
            {
                "customer_name": "Test Customer",
            }
        )
        self.assertTrue(sac.display_name.endswith("Test Customer"))
