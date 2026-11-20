A user sees a journal, and the entries, journal items, payments and bank
statement lines posted in it, when the journal has no allowed groups or
when the user belongs to one of its allowed groups. The other journals do
not appear in lists, searches, selections or reports, and opening or
creating a record in them raises an access error.

The default journal of a new invoice, bill or payment is chosen among the
journals visible to the user. When a new invoice or bill would use a
journal type for which the user has no visible journal, the error message
says that none of the groups of the user is allowed in a journal of that
type.

Changes of the allowed groups of a journal, or of the groups of a user,
apply immediately, without restarting the server.
