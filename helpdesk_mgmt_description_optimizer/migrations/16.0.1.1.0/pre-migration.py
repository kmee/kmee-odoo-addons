# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'helpdesk_ticket' "
        "AND column_name = 'description_full'"
    )
    if not cr.fetchone():
        return
    cr.execute(
        "UPDATE helpdesk_ticket "
        "SET description = description_full "
        "WHERE description_full IS NOT NULL AND description_full <> ''"
    )
