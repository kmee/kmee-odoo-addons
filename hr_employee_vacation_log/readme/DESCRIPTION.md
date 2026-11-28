Simple log of the vacations taken by each employee, for companies that do not
run payroll in Odoo and only need to know who has vacation to take.

- **Accrual periods** per employee, with the entitled days, the days already
  taken and the remaining balance.
- **Vacations taken** (start, end, days), flagged when part of them is sold
  (cash bonus) or when the first installment of the 13th salary is paid with
  them.
- **Vacation schedule report** by department or employee, to plan the next
  vacations.

It does not depend on the leave or payroll modules. Companies that run the
Brazilian payroll should use `l10n_br_hr_vacation` instead.
