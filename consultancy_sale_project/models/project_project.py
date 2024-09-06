from odoo import models


class ProjectProject(models.Model):
    _inherit = "project.project"

    def action_update_project_lines(self):
        contract = self.contract_id
        contract_products = contract.mapped("contract_line_fixed_ids.product_id")

        for employee in self.env["hr.employee"].search([]):
            for product_line in employee.product_line_ids:
                product = product_line.product_tmpl_id.product_variant_id
                contract_line = contract.contract_line_fixed_ids.filtered(
                    lambda line: line.product_id == product
                )
                if (
                    product in contract_products
                    and employee in product_line.product_tmpl_id.employee_line_ids
                    and product_line.product_tmpl_id == product.product_tmpl_id
                ):
                    existing_line = self.sale_line_employee_ids.filtered(
                        lambda line: line.product_id == product
                        and line.employee_id == employee
                    )
                    if existing_line:
                        existing_line.write(
                            {
                                "price_unit": product.lst_price,
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
                                            "product_id": product.id,
                                            "contract_line_id": contract_line.id,
                                            "contract_id": contract.id,
                                            "price_unit": product.lst_price,
                                            "employee_id": employee.id,
                                        },
                                    )
                                ]
                            }
                        )
