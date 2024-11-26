from odoo import models


class ProjectProject(models.Model):
    _inherit = "project.project"

    def action_update_project_lines(self):
        contract = self.contract_id
        contract_products = contract.mapped("contract_line_fixed_ids.product_id")

        for employee in self.env["hr.employee"].search([]):
            for product_template in employee.product_line_ids:
                product_variant = product_template.product_variant_id
                contract_line = contract.contract_line_fixed_ids.filtered(
                    lambda line: line.product_id == product_variant
                )[:1]

                if product_variant in contract_products:
                    existing_line = self.sale_line_employee_ids.filtered(
                        lambda line: line.product_id == product_variant
                        and line.employee_id == employee
                    )
                    if existing_line:
                        existing_line.write(
                            {
                                "price_unit": product_variant.lst_price,
                            }
                        )
                    else:
                        self.write(
                            {
                                "sale_line_employee_ids": [
                                    (
                                        0,
                                        0,
                                        {
                                            "product_id": product_variant.id,
                                            "contract_line_id": contract_line.id,
                                            "contract_id": contract.id,
                                            "price_unit": product_variant.lst_price,
                                            "employee_id": employee.id,
                                        },
                                    )
                                ]
                            }
                        )
