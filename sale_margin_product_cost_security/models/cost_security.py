# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import api, models

COST_GROUP = "product_cost_security.group_product_cost"

# read_group field specs: "field", "field:agg" or "alias:agg(field)"
_FIELD_SPEC = re.compile(r"^\s*(\w+)(?::\w+(?:\((\w+)\))?)?\s*$")


class SaleCostSecurityMixin(models.AbstractModel):
    """Enforce the product cost group on read_group.

    Fields with ``groups`` are already protected on read/write by the ORM, but
    in this version ``read_group`` does not check field groups, so the cost
    and the margin could still be summed by RPC. Odoo 17 does this check in
    the ORM itself.
    """

    _name = "sale.cost.security.mixin"
    _description = "Sale cost access control on grouped reads"

    @api.model
    def _cost_security_fields(self):
        return {
            name
            for name, field in self._fields.items()
            if COST_GROUP in str(field.groups).split(",")
        }

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        if not self.env.su:
            if not fields:
                # an empty list means every stored field: drop the forbidden ones
                fields = [
                    name
                    for name in self.check_field_access_rights("read", None)
                    if self._fields[name].store
                ]
            names = set()
            for spec in fields:
                match = _FIELD_SPEC.match(spec)
                if match:
                    names.add(match.group(2) or match.group(1))
            groupbys = [groupby] if isinstance(groupby, str) else list(groupby or [])
            names.update(spec.split(":")[0].strip() for spec in groupbys)
            self.check_field_access_rights(
                "read", sorted(names & self._cost_security_fields())
            )
        return super().read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
