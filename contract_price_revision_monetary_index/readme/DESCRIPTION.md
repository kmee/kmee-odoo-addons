This module revises the prices of recurring contracts on their anniversary
by a monetary index (a consumer price index such as IPCA, INPC or IGP-M,
or any index of *Monetary Index Update*), without typing the percentage.

The revision uses the mechanism of *Contract Price Revision*: the current
line ends on the day before the revision date and a successor line starts
with the revised price, so the price history stays in the contract and
invoices already issued do not change.

The variation is the compound variation of the monthly rates of the index
over the months of the period (by default the twelve months that end in the
month before the revision). While any month of the period is not published,
the revision waits.

Each contract chooses how the revision is applied: an activity for the
responsible to review and approve (default), or automatically on the
revision date. It works for customer and supplier contracts.
