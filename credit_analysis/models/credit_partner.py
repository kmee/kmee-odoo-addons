# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CreditPartner(models.Model):
    _name = "credit.partner"
    _description = "Socio da Empresa"
    _order = "participation desc, name"

    company_id = fields.Many2one(
        comodel_name="credit.company",
        string="Empresa",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        string="Nome",
        required=True,
    )
    document = fields.Char(
        string="CPF/CNPJ",
    )
    document_type = fields.Selection(
        selection=[
            ("cpf", "CPF"),
            ("cnpj", "CNPJ"),
        ],
        string="Tipo de Documento",
        default="cpf",
    )
    participation = fields.Float(
        string="Participacao (%)",
        digits=(5, 2),
    )
    entry_date = fields.Date(
        string="Data de Entrada",
    )
    signs_company = fields.Boolean(
        string="Assina pela Empresa",
        default=False,
    )
    situation = fields.Selection(
        selection=[
            ("regular", "Regular"),
            ("irregular", "Irregular"),
        ],
        string="Situacao",
        default="regular",
    )
    has_debts = fields.Boolean(
        string="Possui Debitos",
        default=False,
    )
    has_fraud = fields.Boolean(
        string="Possui Fraude",
        default=False,
    )
    negativacoes_value = fields.Monetary(
        string="Valor Negativacoes",
        currency_field="currency_id",
    )
    protestos_value = fields.Monetary(
        string="Valor Protestos",
        currency_field="currency_id",
    )
    acoes_value = fields.Monetary(
        string="Valor Acoes Judiciais",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moeda",
        default=lambda self: self.env.company.currency_id,
    )

    # Participations in other companies
    participation_ids = fields.One2many(
        comodel_name="credit.partner.participation",
        inverse_name="partner_id",
        string="Participacoes em Outras Empresas",
    )
    participation_count = fields.Integer(
        string="Qtd Participacoes",
        compute="_compute_participation_count",
    )

    # Computed fields
    document_formatted = fields.Char(
        string="Documento Formatado",
        compute="_compute_document_formatted",
    )
    total_restrictions = fields.Monetary(
        string="Total Restricoes",
        compute="_compute_total_restrictions",
        currency_field="currency_id",
    )

    @api.depends("participation_ids")
    def _compute_participation_count(self):
        for record in self:
            record.participation_count = len(record.participation_ids)

    @api.depends("document", "document_type")
    def _compute_document_formatted(self):
        for record in self:
            if record.document:
                doc_clean = re.sub(r"\D", "", record.document)
                if record.document_type == "cpf" and len(doc_clean) == 11:
                    record.document_formatted = (
                        f"{doc_clean[:3]}.{doc_clean[3:6]}."
                        f"{doc_clean[6:9]}-{doc_clean[9:]}"
                    )
                elif record.document_type == "cnpj" and len(doc_clean) == 14:
                    record.document_formatted = (
                        f"{doc_clean[:2]}.{doc_clean[2:5]}."
                        f"{doc_clean[5:8]}/{doc_clean[8:12]}-{doc_clean[12:]}"
                    )
                else:
                    record.document_formatted = record.document
            else:
                record.document_formatted = ""

    @api.depends("negativacoes_value", "protestos_value", "acoes_value")
    def _compute_total_restrictions(self):
        for record in self:
            record.total_restrictions = (
                record.negativacoes_value
                + record.protestos_value
                + record.acoes_value
            )

    @api.constrains("participation")
    def _check_participation(self):
        for record in self:
            if record.participation < 0 or record.participation > 100:
                raise ValidationError(
                    _("A participacao deve estar entre 0 e 100%.")
                )

    @api.constrains("document", "document_type")
    def _check_document(self):
        for record in self:
            if record.document:
                doc_clean = re.sub(r"\D", "", record.document)
                if record.document_type == "cpf":
                    if not self._validate_cpf(doc_clean):
                        raise ValidationError(
                            _("CPF invalido: %s") % record.document
                        )
                elif record.document_type == "cnpj":
                    if not self._validate_cnpj(doc_clean):
                        raise ValidationError(
                            _("CNPJ invalido: %s") % record.document
                        )

    @api.model
    def _validate_cpf(self, cpf):
        """Validate CPF with check digit verification."""
        if len(cpf) != 11:
            return False
        if cpf == cpf[0] * 11:
            return False
        # First check digit
        sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        d1 = (sum1 * 10) % 11
        d1 = 0 if d1 == 10 else d1
        if int(cpf[9]) != d1:
            return False
        # Second check digit
        sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        d2 = (sum2 * 10) % 11
        d2 = 0 if d2 == 10 else d2
        if int(cpf[10]) != d2:
            return False
        return True

    @api.model
    def _validate_cnpj(self, cnpj):
        """Validate CNPJ with check digit verification."""
        if len(cnpj) != 14:
            return False
        if cnpj == cnpj[0] * 14:
            return False
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum1 = sum(int(cnpj[i]) * weights1[i] for i in range(12))
        d1 = 11 - (sum1 % 11)
        d1 = 0 if d1 >= 10 else d1
        if int(cnpj[12]) != d1:
            return False
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum2 = sum(int(cnpj[i]) * weights2[i] for i in range(13))
        d2 = 11 - (sum2 % 11)
        d2 = 0 if d2 >= 10 else d2
        if int(cnpj[13]) != d2:
            return False
        return True

    @api.onchange("document", "document_type")
    def _onchange_document(self):
        if self.document:
            doc_clean = re.sub(r"\D", "", self.document)
            if self.document_type == "cpf" and len(doc_clean) == 11:
                self.document = (
                    f"{doc_clean[:3]}.{doc_clean[3:6]}."
                    f"{doc_clean[6:9]}-{doc_clean[9:]}"
                )
            elif self.document_type == "cnpj" and len(doc_clean) == 14:
                self.document = (
                    f"{doc_clean[:2]}.{doc_clean[2:5]}."
                    f"{doc_clean[5:8]}/{doc_clean[8:12]}-{doc_clean[12:]}"
                )

    def action_view_participations(self):
        """View participations in other companies."""
        self.ensure_one()
        return {
            "name": _("Participacoes em Outras Empresas"),
            "type": "ir.actions.act_window",
            "res_model": "credit.partner.participation",
            "view_mode": "tree,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
