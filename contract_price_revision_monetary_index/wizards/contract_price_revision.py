# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ContractPriceRevisionWizard(models.TransientModel):
    _inherit = "contract.price.revision.wizard"

    index_preview = fields.Html(
        string="Revision by Index",
        compute="_compute_index_preview",
        sanitize=False,
    )

    @api.model
    def _get_variation_type(self):
        return super()._get_variation_type() + [("index", "Monetary Index")]

    def _get_index_contracts(self):
        contracts = self.env["contract.contract"].browse(
            self.env.context.get("active_ids") or []
        )
        return contracts.filtered("revision_index_id")

    @api.depends("variation_type", "date_start")
    def _compute_index_preview(self):
        for wizard in self:
            if wizard.variation_type != "index" or not wizard.date_start:
                wizard.index_preview = False
                continue
            blocks = []
            for contract in wizard._get_index_contracts():
                try:
                    info = contract._get_monetary_index_revision(wizard.date_start)
                    text = contract._monetary_index_revision_html(info)
                except UserError as exc:
                    text = exc.args[0]
                blocks.append(
                    Markup("<p><b>%s</b><br/>%s</p>") % (contract.display_name, text)
                )
            wizard.index_preview = Markup("").join(blocks) or _(
                "None of the selected contracts has a revision index."
            )

    def _get_index_info(self, line):
        return self.env.context["monetary_index_revision"][line.contract_id.id]

    def _get_new_price(self, line):
        if self.variation_type == "index":
            info = self._get_index_info(line)
            return line.price_unit * (1.0 + info["percent"] / 100.0)
        return super()._get_new_price(line)

    def _get_new_line_value(self, line):
        values = super()._get_new_line_value(line)
        if self.variation_type == "index":
            info = self._get_index_info(line)
            values.update(
                {
                    "revision_index_id": info["index"].id,
                    "revision_period_start": info["date_from"],
                    "revision_period_end": info["date_to"],
                    "revision_factor": info["factor"],
                    "revision_percent": info["percent"],
                }
            )
        return values

    def _get_contract_lines_to_revise(self, contracts):
        if self.variation_type == "index":
            contracts = contracts.filtered("revision_index_id")
        return super()._get_contract_lines_to_revise(contracts)

    def action_apply(self):
        if self.variation_type != "index":
            return super().action_apply()
        self.ensure_one()
        contracts = self._get_index_contracts()
        if not contracts:
            raise UserError(_("None of the selected contracts has a revision index."))
        # raises while a month of any period is not published
        infos = {
            contract.id: contract._get_monetary_index_revision(self.date_start)
            for contract in contracts
        }
        action = super(
            ContractPriceRevisionWizard,
            self.with_context(monetary_index_revision=infos),
        ).action_apply()
        for contract in contracts:
            contract._after_monetary_index_revision(infos[contract.id])
        return action
