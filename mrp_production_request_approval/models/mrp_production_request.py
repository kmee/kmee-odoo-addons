# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class MrpProductionRequest(models.Model):
    _inherit = "mrp.production.request"

    assigned_to_ids = fields.Many2many(
        comodel_name="res.users",
        string="Approvers",
        tracking=True,
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref(
                    "mrp_production_request.group_mrp_production_request_manager"
                ).id,
            )
        ],
        help="Users allowed to approve and reopen the request. When empty, any "
        "manager can.",
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
        copy=False,
        tracking=True,
    )
    approved_datetime = fields.Datetime(
        string="Approved on",
        readonly=True,
        copy=False,
    )

    def _check_user_is_approver(self):
        for request in self:
            if request.assigned_to_ids and self.env.user not in request.assigned_to_ids:
                raise UserError(
                    _(
                        "Only the approvers of request %(name)s can do this: "
                        "%(approvers)s.",
                        name=request.name,
                        approvers=", ".join(request.assigned_to_ids.mapped("name")),
                    )
                )

    def button_approved(self):
        self._check_user_is_approver()
        res = super().button_approved()
        self.write(
            {
                "approved_by": self.env.user.id,
                "approved_datetime": fields.Datetime.now(),
            }
        )
        return res

    def button_reopen(self):
        self._check_user_is_approver()
        self.write({"state": "approved"})
        return True
