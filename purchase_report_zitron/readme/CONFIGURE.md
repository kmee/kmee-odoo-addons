The report paper format is installed by the module. The fixed note printed at
the end of the last page is edited in the company form, tab Purchase Report.

The note has no default value: it is empty until configured, and the PDF omits
the block while it is empty. Set the text per company (billing instructions,
payment schedule, contacts) through the deployment data or the company form,
never in the module code.

Compatibility: this module replaces the purchase order document templates and
sets the landscape paper format on the standard "Purchase Order" and "Request
for Quotation" actions, so it applies to every company of the database. The
templates are a global replacement of the core ones, so the paper format
cannot be scoped to one company without a per-company template switch; install
it only in databases where this layout is wanted for all companies.
