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

    @api.depends('name', 'parent_id')
    def _compute_display_name(self):
        for tag in self:
            names = []
            current = tag.parent_id
            while current:
                names.append(current.name)
                current = current.parent_id
            tag.display_name = " / ".join(reversed(names))

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if self._has_cycle("parent_id"):
            raise ValidationError(self.env._("Tags cannot be recursive."))
