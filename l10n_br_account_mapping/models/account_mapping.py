# Copyright (C) 2026 KMEE Informatica LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMappingPlan(models.Model):
    """Plano de contas de destino.

    Representa um plano de contas externo ao Odoo: o plano do escritorio de
    contabilidade que recebe a exportacao, ou o plano referencial da RFB usado
    no registro I051 do SPED Contabil (ECD). Uma empresa pode ter varios planos
    ao mesmo tempo (dois escritorios, transicao, referencial).

    O desenho espelha o account_consolidation do Odoo Enterprise
    (consolidation.chart / consolidation.account), sem depender dele: o
    registro central e a conta DO DESTINO, e um many2many diz quais contas do
    Odoo desaguam nela (N:1).
    """

    _name = "l10n_br_account_mapping.plan"
    _description = "Plano de Contas de Destino"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        help="Vazio vale para todas as empresas.",
    )
    account_ids = fields.One2many(
        comodel_name="l10n_br_account_mapping.account",
        inverse_name="plan_id",
        string="Contas do plano",
    )
    account_count = fields.Integer(compute="_compute_counts")
    mapped_count = fields.Integer(
        compute="_compute_counts",
        help="Quantas contas do Odoo estao vinculadas a alguma conta deste plano.",
    )

    @api.depends("account_ids.account_ids")
    def _compute_counts(self):
        for plan in self:
            plan.account_count = len(plan.account_ids)
            plan.mapped_count = len(plan.account_ids.account_ids)

    def resolve(self, account, date=None):
        """Conta do destino em que a conta do Odoo desagua neste plano.

        Devolve um recordset de ``l10n_br_account_mapping.account`` (vazio
        quando a conta nao esta mapeada). A constraint de ambiguidade garante
        no maximo um resultado vigente por plano.

        :param date: quando informada, so valem as contas do destino vigentes
            nessa data (ECD/ECF retificadora de anos anteriores usa a tabela
            da epoca, nao a atual).
        """
        self.ensure_one()
        if not account:
            return self.env["l10n_br_account_mapping.account"]
        domain = [("plan_id", "=", self.id), ("account_ids", "in", account.id)]
        if date:
            domain += [
                "|",
                ("date_start", "=", False),
                ("date_start", "<=", date),
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", date),
            ]
        return self.env["l10n_br_account_mapping.account"].search(domain, limit=1)

    def unmapped_odoo_accounts(self, accounts):
        """Dentre ``accounts``, as que nao caem em nenhuma conta deste plano."""
        self.ensure_one()
        return accounts - self.account_ids.account_ids


class AccountMappingAccount(models.Model):
    """Uma conta do plano de destino, com as contas do Odoo que caem nela."""

    _name = "l10n_br_account_mapping.account"
    _description = "Conta do Plano de Destino"
    _order = "code, name"
    _rec_name = "display_code_name"

    plan_id = fields.Many2one(
        comodel_name="l10n_br_account_mapping.plan",
        string="Plano",
        required=True,
        ondelete="cascade",
        index=True,
    )
    code = fields.Char(
        string="Codigo no destino",
        required=True,
        size=20,
        index=True,
    )
    name = fields.Char(
        string="Nome no destino",
        required=True,
        help="Nome da conta como o destino a conhece. E o que sai no plano de "
        "contas exportado e no I051 do SPED.",
    )
    display_code_name = fields.Char(compute="_compute_display_code_name")
    date_start = fields.Date(
        string="Vigencia inicial",
        help="Inicio de vigencia da conta no destino. Vazio vale desde sempre.",
    )
    date_end = fields.Date(
        string="Vigencia final",
        help="Fim de vigencia; vazio quando a conta segue vigente.",
    )
    account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="l10n_br_account_mapping_account_rel",
        column1="mapping_account_id",
        column2="account_id",
        string="Contas do Odoo",
        help="Contas do plano do Odoo que desaguam nesta conta do destino "
        "(varias contas podem cair na mesma).",
    )

    _sql_constraints = [
        (
            "code_plan_uniq",
            "unique (plan_id, code)",
            "Ja existe uma conta com este codigo neste plano de destino.",
        )
    ]

    @api.depends("code", "name")
    def _compute_display_code_name(self):
        for rec in self:
            rec.display_code_name = f"{rec.code} - {rec.name}"

    @api.constrains("account_ids", "plan_id")
    def _check_account_uniqueness_in_plan(self):
        """Uma conta do Odoo so pode desaguar numa conta por plano.

        Sem isso o codigo exportado seria ambiguo: a mesma conta do Odoo
        resolveria para dois codigos diferentes do mesmo destino. A checagem
        e uma consulta por plano na tabela de ligacao (a carga oficial tem
        milhares de contas por plano; uma busca por registro nao escala).
        """
        if not any(rec.account_ids for rec in self):
            return
        for plan in self.plan_id:
            self.env.cr.execute(
                """
                SELECT rel.account_id
                FROM l10n_br_account_mapping_account_rel rel
                JOIN l10n_br_account_mapping_account ma
                    ON ma.id = rel.mapping_account_id
                WHERE ma.plan_id = %s
                GROUP BY rel.account_id
                HAVING count(*) > 1
                """,
                (plan.id,),
            )
            duplicated_ids = [row[0] for row in self.env.cr.fetchall()]
            if duplicated_ids:
                duplicated = self.env["account.account"].browse(duplicated_ids)
                raise ValidationError(
                    _(
                        "As contas %(contas)s ja estao vinculadas a outra conta "
                        "do plano %(plano)s. Uma conta do Odoo so pode desaguar "
                        "em uma conta por plano de destino."
                    )
                    % {
                        "contas": ", ".join(duplicated.mapped("code")),
                        "plano": plan.name,
                    }
                )


class AccountAccount(models.Model):
    _inherit = "account.account"

    l10n_br_mapping_account_ids = fields.Many2many(
        comodel_name="l10n_br_account_mapping.account",
        relation="l10n_br_account_mapping_account_rel",
        column1="account_id",
        column2="mapping_account_id",
        string="Contas de destino",
        help="Em quais contas dos planos de destino esta conta desagua.",
    )
