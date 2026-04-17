==================
L10n Br NFe Rastro
==================

Integrates ``nfe40_rastro`` traceability data from ``stock.lot`` into NF-e
(Brazilian electronic invoice). Populates lot number, production date
and expiry date on fiscal document lines from stock move lots.

Configuration
=============

1. Navigate to **Inventory > Configuration > Settings** and enable:

   - **Lots & Serial Numbers**
   - **Expiration Dates**

2. For relevant products, set **Tracking** to "By Lots".

3. When creating invoices from pickings, the rastro data will be
   automatically populated from the stock lot information.

Credits
=======

Authors
~~~~~~~

* KMEE

Maintainers
~~~~~~~~~~~

* KMEE - https://www.kmee.com.br
