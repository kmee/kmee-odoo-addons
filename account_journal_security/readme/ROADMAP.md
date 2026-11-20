- Accounting reports (trial balance, general ledger, MIS Builder and
  others) read journal items with the rights of the user: for a restricted
  user they only show the visible journals and come out partial.
- Every user who posts needs at least one visible journal of each type he
  uses: an invoice needs a sales journal, a bill a purchase journal.
- Registering a payment needs a visible bank or cash journal.
- Reconciliation between journals of different groups (for instance an
  invoice and a payment of another team) and the Enterprise accounting
  screens were not evaluated.
- Bank statements (the statement records, not their lines), analytic items
  and reconciliation models are not restricted.
- For 19.0, the groups of a user are in another field (`group_ids` instead
  of `groups_id`): the record rules have to be adapted in the migration.
- To choose the default journal among the visible ones, the journal of
  entries and payments is computed with the rights of the user instead of
  as superuser. A module that overrides that computation and reads records
  the user cannot access has to be checked.
