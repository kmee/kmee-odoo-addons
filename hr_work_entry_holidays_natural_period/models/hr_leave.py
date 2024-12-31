# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class HrLeave(models.Model):
    _inherit = "hr.leave"

    def _get_number_of_days_batch(self, date_from, date_to, employee_ids):
        """Sobrescrevce a função para não chamar a do hr_work_entry_holidays"""
        employee = self.env["hr.employee"].browse(employee_ids)
        # We force the company in the domain as we are more than likely in a compute_sudo
        domain = [
            ("time_type", "=", "leave"),
            (
                "company_id",
                "in",
                self.env.company.ids + self.env.context.get("allowed_company_ids", []),
            ),
        ]

        result = employee._get_work_days_data_batch(date_from, date_to, domain=domain)
        for employee_id in result:
            if self.request_unit_half and result[employee_id]["hours"] > 0:
                result[employee_id]["days"] = 0.5
        return result
