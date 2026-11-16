This module fetches Brazilian monetary indexes from the Time Series
Management System (SGS) of the Banco Central do Brasil (BCB) into
*Monetary Index Update*.

It comes with SELIC (SGS series 4390), IPCA (433), INPC (188) and IGP-M
(189). Any other SGS series is fetched by setting its code on the index.

It replaces *monetary_index_update_selic*: in a database that has the old
module installed, updating *monetary_index_update* renames it and keeps its
records.
