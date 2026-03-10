from odoo import _, fields, models
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_br_esocial_s1200_id = fields.Many2one(
        "l10n_br.esocial.s1200",
        string="S-1200 eSocial",
        readonly=True,
    )

    def action_esocial_gerar_s1200(self):
        """Generate S-1200 event for selected confirmed payslips."""
        payslips = self.filtered(lambda p: p.state == "done")
        if not payslips:
            raise UserError(
                _("Selecione apenas holerites confirmados (estado 'Feito').")
            )

        # Group by employee + period
        groups = {}
        for slip in payslips:
            key = (slip.employee_id.id, slip.date_from.strftime("%Y-%m"))
            groups.setdefault(key, self.env["hr.payslip"])
            groups[key] |= slip

        created_events = self.env["l10n_br.esocial.evento"]
        for (emp_id, per_apur), slips in groups.items():
            s1200 = self.env["l10n_br.esocial.s1200"].create(
                {
                    "employee_id": emp_id,
                    "payslip_ids": [(6, 0, slips.ids)],
                    "per_apur": per_apur,
                    "ind_apuracao": "1",
                    "company_id": slips[0].company_id.id,
                }
            )
            evento = s1200.action_gerar_evento()
            created_events |= evento
            slips.write({"l10n_br_esocial_s1200_id": s1200.id})

        if len(created_events) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "l10n_br.esocial.evento",
                "res_id": created_events.id,
                "view_mode": "form",
            }
        return {
            "type": "ir.actions.act_window",
            "res_model": "l10n_br.esocial.evento",
            "view_mode": "tree,form",
            "domain": [("id", "in", created_events.ids)],
        }
