===================================
Hr Leave Custom Hour Interval 5 Min
===================================

**Deprecated since 18.0: this module is not installable anymore.**

Up to Odoo 17.0, the time off fields ``request_hour_from`` and
``request_hour_to`` are selection fields with 30 minute steps, and this module
replaces them with 5 minute steps.

Since Odoo 18.0, the core defines both fields as float fields, shown with the
``float_time_selection`` widget, so any minute can be typed in the time off
form. The module is therefore redundant, and redefining the fields as
selections would conflict with the core onchange that keeps the hours in range
and in order.

Use the standard Odoo fields instead and uninstall this module when upgrading
a database from 17.0.
