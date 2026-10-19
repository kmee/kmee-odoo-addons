from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDisplayNameRef(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"].with_context(tracking_disable=True)

    def test_name_get_prefixes_reference(self):
        """Given a partner with a reference, When reading its name_get,
        Then the reference is shown in brackets before the name."""
        partner = self.Partner.create({"name": "Acme", "ref": "C-100"})
        self.assertEqual(partner.name_get()[0][1], "[C-100] Acme")

    def test_name_get_without_reference(self):
        """Given a partner without reference, Then the name has no brackets."""
        partner = self.Partner.create({"name": "Acme"})
        self.assertEqual(partner.name_get()[0][1], "Acme")

    def test_display_name_follows_reference_change(self):
        """Given a partner, When the reference is set and then removed,
        Then display_name reflects each state."""
        partner = self.Partner.create({"name": "Acme"})
        partner.ref = "X1"
        self.assertEqual(partner.display_name, "[X1] Acme")
        partner.ref = False
        self.assertEqual(partner.display_name, "Acme")

    def test_child_contact_keeps_company_prefix_and_own_ref(self):
        """Given a company contact with own reference, Then the parent name is
        kept and the child's reference prefixes the composite name."""
        parent = self.Partner.create({"name": "Parent Co", "is_company": True})
        child = self.Partner.create(
            {"name": "John", "parent_id": parent.id, "ref": "J-1"}
        )
        self.assertEqual(child.name_get()[0][1], "[J-1] Parent Co, John")

    def test_name_search_still_finds_by_name(self):
        """Given a partner with reference, When searching by name,
        Then it is found and the displayed name contains the reference."""
        partner = self.Partner.create({"name": "Zyxwv Corp", "ref": "R-9"})
        result = self.Partner.name_search("Zyxwv")
        self.assertIn((partner.id, "[R-9] Zyxwv Corp"), result)

    def test_multiple_partners_name_get(self):
        """Given several partners, Then each gets its own prefix."""
        a = self.Partner.create({"name": "A", "ref": "1"})
        b = self.Partner.create({"name": "B"})
        names = dict((a | b).name_get())
        self.assertEqual(names[a.id], "[1] A")
        self.assertEqual(names[b.id], "B")
