In Odoo 18 the only menu for payment terms is Invoicing > Configuration >
Invoicing > Payment Terms, visible only to accounting groups, and the payment
terms field of the purchase order cannot create records on the fly. Purchasing
users therefore could not create or maintain payment terms without access to
the Invoicing app.

This module adds the opt-in group "Manage Payment Terms from Purchase" and the
menu Purchase > Configuration > Payment Terms for its members. The group grants
read, write and create access on payment terms and their lines. Deleting
payment terms stays restricted to accounting. Installing the module does not
change the access of any existing user.
