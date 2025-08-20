# Copyright (C) 2025-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from random import randint

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPickingTag(models.Model):
    _name = "stock.picking.tag"
    _description = "Stock Picking Tag"
    _parent_store = True

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char("Tag Name", required=True, translate=True)
    color = fields.Integer(default=lambda self: self._get_default_color())
    parent_id = fields.Many2one("stock.picking.tag", index=True, ondelete="cascade")
    child_ids = fields.One2many("stock.picking.tag", "parent_id")
    parent_path = fields.Char(index=True)

    _sql_constraints = [
        ("tag_name_uniq", "unique (name)", "Tag name already exists!"),
    ]

    def name_get(self):
        res = []
        for tag in self:
            names = []
            current = tag
            while current:
                names.append(current.name)
                current = current.parent_id
            res.append((tag.id, " / ".join(reversed(names))))
        return res

    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        if name:
            args = [("name", operator, name.split(" / ")[-1])] + list(args or [])
        return super()._name_search(
            name=name,
            args=args,
            operator=operator,
            limit=limit,
            name_get_uid=name_get_uid,
        )

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if not self._check_recursion("parent_id"):
            raise ValidationError(_("Tags cannot be recursive."))
