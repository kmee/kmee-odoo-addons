This module adds a **Summary** tab on stock pickings (transfers) that groups operations
by product and unit of measure. When multiple moves share the same product and UoM,
their demand and done quantities are summed into a single line.

- A computed field indicates when a summary view is available (i.e. when there are
  duplicate product+UoM lines).
- When the summary differs from the full operations list, an alert appears on the
  Operations page with a link that opens the Summary tab.
- The Summary tab shows a read-only list of grouped lines (product, UoM, demand, done).
  Summary data is computed when the form is opened.
