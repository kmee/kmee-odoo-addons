# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta
from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round, format_date


class ContractContract(models.Model):
    _inherit = "contract.contract"

    revision_index_id = fields.Many2one(
        comodel_name="monetary.index",
        string="Revision Index",
        help="Monetary index (e.g. IPCA) used to revise the prices of this contract "
        "on every anniversary.",
    )
    revision_interval = fields.Integer(
        string="Revision Interval (months)",
        default=12,
        help="Months between two revisions; also the number of monthly rates "
        "accumulated in each revision.",
    )
    revision_date_base = fields.Date(
        string="Revision Base Date",
        compute="_compute_revision_date_base",
        store=True,
        readonly=False,
        help="Date of the last price setting (the contract start by default). "
        "The next revision is this date plus the revision interval.",
    )
    revision_next_date = fields.Date(
        string="Next Revision",
        compute="_compute_revision_next_date",
        store=True,
        readonly=False,
    )
    revision_index_lag = fields.Integer(
        string="Index Lag (months)",
        default=1,
        help="The accumulated period ends this many months before the month of the "
        "revision. With 1, a revision in December uses the twelve months up to "
        "November.",
    )
    revision_negative_policy = fields.Selection(
        selection=[
            ("ignore", "Do not reduce prices"),
            ("apply", "Apply negative variation"),
        ],
        string="Negative Variation",
        default="ignore",
        required=True,
    )
    revision_cap = fields.Float(
        string="Revision Cap (%)",
        digits=(16, 4),
        help="Maximum variation applied in one revision. Zero means no cap.",
    )
    revision_mode = fields.Selection(
        selection=[
            ("approval", "Schedule an activity for approval"),
            ("auto", "Apply automatically"),
        ],
        default="approval",
        required=True,
    )

    @api.depends("date_start")
    def _compute_revision_date_base(self):
        for contract in self:
            contract.revision_date_base = (
                contract.revision_date_base or contract.date_start
            )

    @api.depends("revision_date_base", "revision_interval", "revision_index_id")
    def _compute_revision_next_date(self):
        for contract in self:
            if (
                contract.revision_index_id
                and contract.revision_date_base
                and contract.revision_interval > 0
            ):
                contract.revision_next_date = contract.revision_date_base + (
                    relativedelta(months=contract.revision_interval)
                )
            else:
                contract.revision_next_date = False

    def _get_monetary_index_period(self, revision_date):
        """First and last day of the accumulated period for a revision date."""
        self.ensure_one()
        last_month = revision_date.replace(day=1) - relativedelta(
            months=self.revision_index_lag
        )
        first_month = last_month - relativedelta(months=self.revision_interval - 1)
        last_day = last_month + relativedelta(months=1, days=-1)
        return first_month, last_day

    def _get_monetary_index_revision(self, revision_date=None):
        """Accumulated variation of the index for a revision.

        Raise UserError while any month of the period has no published rate: the
        revision never runs with a missing month.
        """
        self.ensure_one()
        if not self.revision_index_id:
            raise UserError(
                _("Contract %(name)s has no revision index.") % {"name": self.name}
            )
        if self.revision_interval <= 0:
            raise UserError(_("The revision interval must be positive."))
        revision_date = revision_date or self.revision_next_date
        if not revision_date:
            raise UserError(
                _("Contract %(name)s has no revision date.") % {"name": self.name}
            )
        date_from, date_to = self._get_monetary_index_period(revision_date)
        rates = self.env["monetary.index.rate"].search(
            [
                ("index_id", "=", self.revision_index_id.id),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
            ],
            order="date asc",
        )
        months = {(rate.date.year, rate.date.month) for rate in rates}
        expected = [
            date_from + relativedelta(months=i) for i in range(self.revision_interval)
        ]
        missing = [d for d in expected if (d.year, d.month) not in months]
        if missing:
            raise UserError(
                _(
                    "Index %(index)s has no rate for %(months)s: the revision of "
                    "contract %(name)s waits for the publication."
                )
                % {
                    "index": self.revision_index_id.name,
                    "months": ", ".join(d.strftime("%m/%Y") for d in missing),
                    "name": self.name,
                }
            )
        # compound, as monetary.update.service.compute_factor, but on the index
        # record itself (the service looks the index up by code)
        factor = 1.0
        for rate in rates:
            factor *= 1.0 + rate.value / 100.0
        percent_index = (factor - 1.0) * 100.0
        percent = percent_index
        if percent < 0 and self.revision_negative_policy == "ignore":
            percent = 0.0
        if self.revision_cap and percent > self.revision_cap:
            percent = self.revision_cap
        return {
            "index": self.revision_index_id,
            "revision_date": revision_date,
            "date_from": date_from,
            "date_to": date_to,
            "factor": factor,
            "percent_index": float_round(percent_index, precision_digits=4),
            "percent": float_round(percent, precision_digits=4),
        }

    def _monetary_index_revision_html(self, info):
        lines = [
            _("Index: %s") % info["index"].name,
            _("Period: %(from)s to %(to)s")
            % {
                "from": info["date_from"].strftime("%m/%Y"),
                "to": info["date_to"].strftime("%m/%Y"),
            },
            _("Accumulated factor: %.6f") % info["factor"],
            _("Index variation: %.4f%%") % info["percent_index"],
            _("Variation applied: %.4f%%") % info["percent"],
            _("New prices from %s") % format_date(self.env, info["revision_date"]),
        ]
        return Markup("<br/>").join(escape(line) for line in lines)

    def _monetary_index_revision_summary(self, info):
        return _("Revision by %(index)s: %(percent).4f%%") % {
            "index": info["index"].name,
            "percent": info["percent"],
        }

    def action_monetary_index_revision(self):
        """Open the price revision wizard with the index already chosen."""
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "contract_price_revision.contract_line_duplicate_wizard_action"
        )
        dates = set(self.mapped("revision_next_date"))
        action["context"] = {
            "active_ids": self.ids,
            "active_model": self._name,
            "default_variation_type": "index",
            "default_date_start": fields.Date.to_string(dates.pop())
            if len(dates) == 1
            else False,
        }
        return action

    def _apply_monetary_index_revision(self):
        for contract in self:
            wizard = self.env["contract.price.revision.wizard"].create(
                {
                    "date_start": contract.revision_next_date,
                    "variation_type": "index",
                }
            )
            wizard.with_context(
                active_ids=contract.ids, active_model=contract._name
            ).action_apply()

    def _after_monetary_index_revision(self, info):
        """Move the base date, log the revision and close the pending activity."""
        self.ensure_one()
        self.revision_date_base = info["revision_date"]
        self.message_post(
            body=Markup("<p>%s</p><p>%s</p>")
            % (
                _("Prices revised by the index."),
                self._monetary_index_revision_html(info),
            )
        )
        activity_type = self.env.ref(
            "contract_price_revision_monetary_index.mail_activity_contract_revision",
            raise_if_not_found=False,
        )
        if activity_type:
            self.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type
            ).action_feedback(feedback=_("Revision applied."))

    def _get_monetary_index_revision_user(self):
        """Who approves the revision: the contract responsible, else its creator."""
        self.ensure_one()
        return self.user_id or self.create_uid or self.env.user

    @api.model
    def _cron_monetary_index_revision(self, days_ahead=5):
        today = fields.Date.context_today(self)
        contracts = self.search(
            [
                ("revision_index_id", "!=", False),
                ("revision_next_date", "!=", False),
                ("revision_next_date", "<=", today + relativedelta(days=days_ahead)),
            ]
        )
        activity_type = self.env.ref(
            "contract_price_revision_monetary_index.mail_activity_contract_revision"
        )
        for contract in contracts:
            try:
                info = contract._get_monetary_index_revision()
            except UserError:
                continue  # index not published yet: try again tomorrow
            if contract.revision_mode == "auto":
                if contract.revision_next_date <= today:
                    contract._apply_monetary_index_revision()
                continue
            if contract.activity_ids.filtered(
                lambda a, t=activity_type: a.activity_type_id == t
            ):
                continue
            user = contract._get_monetary_index_revision_user()
            # the activity text is written in the language of who approves it
            contract_lang = contract.with_context(lang=user.lang)
            contract.activity_schedule(
                act_type_xmlid=(
                    "contract_price_revision_monetary_index."
                    "mail_activity_contract_revision"
                ),
                date_deadline=contract.revision_next_date,
                summary=contract_lang._monetary_index_revision_summary(info),
                note=contract_lang._monetary_index_revision_html(info),
                user_id=user.id,
            )
