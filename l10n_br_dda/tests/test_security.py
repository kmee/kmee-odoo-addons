# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from .common import PAYER_2, DdaCommon, make_cnpj


class TestSecurity(DdaCommon):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        group = cls.env.ref("l10n_br_dda.group_dda_user")

        def make_user(login, companies):
            return (
                cls.env["res.users"]
                .with_context(no_reset_password=True)
                .create(
                    {
                        "name": login,
                        "login": login,
                        "company_id": companies[0].id,
                        "company_ids": [(6, 0, companies.ids)],
                        "groups_id": [(6, 0, [group.id])],
                    }
                )
            )

        cls.user_1 = make_user("dda_user_company_1", cls.company)
        cls.user_both = make_user("dda_user_both", cls.company | cls.company_2)

    def test_records_are_filtered_by_company(self):
        vendor = make_cnpj("540000010001")
        one = self.upsert(self.boleto(vendor, 10.0, self.day(3)))
        two = self.upsert(self.boleto(vendor, 11.0, self.day(3), payer_cnpj=PAYER_2))
        self.assertEqual(one.company_id, self.company)
        self.assertEqual(two.company_id, self.company_2)
        debit = self.env["l10n_br_dda.debit"]
        seen = debit.with_user(self.user_1).search([("id", "in", (one | two).ids)])
        self.assertEqual(seen, one)
        seen_both = (
            debit.with_user(self.user_both)
            .with_context(allowed_company_ids=(self.company | self.company_2).ids)
            .search([("id", "in", (one | two).ids)])
        )
        self.assertEqual(seen_both, one | two)

    def test_matching_never_crosses_companies(self):
        vendor = self.make_vendor("Vendor Two Companies", "540000020001")
        self.make_bill(vendor, 500.0, self.day(5), company=self.company_2)
        debit = self.upsert(self.boleto(self.cnpj_of(vendor), 500.0, self.day(5)))
        self.assertEqual(debit.company_id, self.company)
        self.assertFalse(debit.match_ids)
        other = self.upsert(
            self.boleto(self.cnpj_of(vendor), 500.0, self.day(5), payer_cnpj=PAYER_2)
        )
        self.assertEqual(len(other.match_ids), 1)

    def test_dashboard_counts_only_allowed_companies(self):
        vendor = make_cnpj("540000030001")
        self.upsert(self.boleto(vendor, 10.0, self.day(-5), payer_cnpj=PAYER_2))
        debit = self.env["l10n_br_dda.debit"]
        before = debit.with_user(self.user_1).dda_dashboard()["counters"]["overdue"]
        self.upsert(self.boleto(vendor, 12.0, self.day(-5)))
        after = debit.with_user(self.user_1).dda_dashboard()["counters"]["overdue"]
        self.assertEqual(after, before + 1)

    def test_technical_payload_is_for_managers(self):
        field = self.env["l10n_br_dda.debit"]._fields["raw_payload"]
        self.assertEqual(field.groups, "l10n_br_dda.group_dda_manager")
