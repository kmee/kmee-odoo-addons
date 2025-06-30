from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ContractSignWizard(models.TransientModel):
    _name = "contract.sign.wizard"
    _description = "Wizard for sending contract for signature"

    contract_id = fields.Many2one("contract.contract", required=True, readonly=True)
    template_id = fields.Many2one(
        "sign.template", string="Sign Template", required=True
    )
    partner_id = fields.Many2one("res.partner", string="Recipient", required=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        contract = self.env["contract.contract"].browse(
            self.env.context.get("active_id")
        )
        template = self.env.ref(
            "sign.sign_template_contract_default", raise_if_not_found=False
        )
        res.update(
            {
                "contract_id": contract.id,
                "partner_id": contract.partner_id.id,
                "template_id": template.id if template else False,
            }
        )
        return res

    def action_confirm(self):
        self.ensure_one()
        if not self.template_id.sign_item_ids:
            raise UserError(_("The sign template must contain at least one item."))

        role = self.template_id.sign_item_ids[0].responsible_id

        sign_request = self.env["sign.request"].create(
            {
                "template_id": self.template_id.id,
                "request_item_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": self.partner_id.id,
                            "role_id": role.id,
                        },
                    )
                ],
                "reference": self.contract_id.name,
                "contract_id": self.contract_id.id,
            }
        )
        self.contract_id.sign_request_id = sign_request
        return {"type": "ir.actions.act_window_close"}
