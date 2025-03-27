from odoo.tests.common import TransactionCase


class TestSac(TransactionCase):

    def setUp(self):
        super(TestSac, self).setUp()
        self.sac_model = self.env['sac']
        self.reason_model = self.env['sac.reason']
        self.type_model = self.env['sac.type']

    def test_create_sac(self):
        """Test SAC creation"""
        sac = self.sac_model.create({
            'customer_name': 'Test Customer',
            'email_from': 'test@example.com',
            'phone': '1234567890',
        })
        self.assertTrue(sac.name.startswith('New'))
        self.assertEqual(sac.customer_name, 'Test Customer')

    def test_compute_display_name(self):
        """Test display name computation"""
        sac = self.sac_model.create({
            'customer_name': 'Test Customer',
        })
        self.assertTrue(sac.display_name.endswith('Test Customer'))
