from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Contract(models.Model):
    _inherit = "hr.contract"

    contract_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Anexos do contrato",
    )

    benefit_type_ids = fields.One2many(
        comodel_name="hr.benefit.line",
        inverse_name="contract_id",
    )

    @api.constrains("benefit_type_ids")
    def _check_dependent(self):
        for contract in self:
            for benefit_line in contract.benefit_type_ids:
                if (
                    len(benefit_line.dependent_ids.ids)
                    > benefit_line.benefit_type_id.max_dependents
                ):
                    raise ValidationError(
                        _(
                            "Não é permitido adicionar mais dependentes do que o limite "
                            "definido no tipo de benefício (%(benefit_name)s), "
                            "(%(max_dependents)s)."
                        )
                        % {
                            "benefit_name": benefit_line.benefit_type_id.name,
                            "max_dependents": benefit_line.benefit_type_id.max_dependents,
                        }
                    )

    @api.constrains("benefit_type_ids")
    def _check_unique_benefit_type(self):
        for contract in self:
            seen_benefit_types = set()
            for benefit_line in contract.benefit_type_ids:
                benefit_type = benefit_line.benefit_type_id
                if benefit_type and benefit_type.id in seen_benefit_types:
                    raise ValidationError(
                        _(
                            "Não é permitido adicionar o mesmo tipo "
                            "de benefício mais de uma vez."
                        )
                    )
                seen_benefit_types.add(benefit_type.id)

    @api.onchange("benefit_type_ids")
    def _onchange_benefit_type_ids(self):
        for benefit_line in self.benefit_type_ids:
            if not benefit_line.beneficiary_id:
                employee = self.employee_id
                if employee and employee.address_home_id:
                    benefit_line.beneficiary_id = employee.address_home_id.id
