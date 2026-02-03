# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CreditCompany(models.Model):
    _name = "credit.company"
    _description = "Empresa para Consulta de Credito"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "razao_social"

    # Basic fields
    cnpj = fields.Char(
        string="CNPJ",
        required=True,
        index="btree",
        tracking=True,
    )
    razao_social = fields.Char(
        string="Razao Social",
        required=True,
        tracking=True,
    )
    nome_fantasia = fields.Char(
        string="Nome Fantasia",
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contato Vinculado",
        tracking=True,
    )
    active = fields.Boolean(
        default=True,
    )

    # Cadastral data (F03)
    natureza_juridica_id = fields.Many2one(
        comodel_name="credit.natureza.juridica",
        string="Natureza Juridica",
        tracking=True,
    )
    data_fundacao = fields.Date(
        string="Data de Fundacao",
        tracking=True,
    )
    data_inicio_atividade = fields.Date(
        string="Data Inicio Atividade",
        tracking=True,
    )
    cnae_principal_id = fields.Many2one(
        comodel_name="credit.cnae",
        string="CNAE Principal",
        tracking=True,
    )
    cnae_secundario_ids = fields.Many2many(
        comodel_name="credit.cnae",
        relation="credit_company_cnae_secundario_rel",
        column1="company_id",
        column2="cnae_id",
        string="CNAEs Secundarios",
    )
    capital_social = fields.Monetary(
        string="Capital Social",
        currency_field="currency_id",
        tracking=True,
    )
    capital_atual = fields.Monetary(
        string="Capital Atual",
        currency_field="currency_id",
        tracking=True,
    )
    situacao_cadastral = fields.Selection(
        selection=[
            ("ativo", "Ativo"),
            ("baixado", "Baixado"),
            ("suspenso", "Suspenso"),
            ("inapto", "Inapto"),
            ("nulo", "Nulo"),
        ],
        string="Situacao Cadastral",
        default="ativo",
        tracking=True,
    )
    data_situacao_cadastral = fields.Date(
        string="Data Situacao Cadastral",
        tracking=True,
    )
    situacao_fgts = fields.Selection(
        selection=[
            ("regular", "Regular"),
            ("irregular", "Irregular"),
            ("nao_informado", "Nao Informado"),
        ],
        string="Situacao FGTS",
        default="nao_informado",
    )
    inscricao_estadual = fields.Char(
        string="Inscricao Estadual",
    )
    uf_inscricao_id = fields.Many2one(
        comodel_name="res.country.state",
        string="UF Inscricao Estadual",
        domain="[('country_id.code', '=', 'BR')]",
    )
    nire = fields.Char(
        string="NIRE",
    )
    uf_nire_id = fields.Many2one(
        comodel_name="res.country.state",
        string="UF NIRE",
        domain="[('country_id.code', '=', 'BR')]",
    )
    orgao_registro = fields.Char(
        string="Orgao de Registro",
    )
    qtd_filiais = fields.Integer(
        string="Quantidade de Filiais",
        default=0,
    )

    # Address fields (F10)
    street = fields.Char(
        string="Logradouro",
    )
    street2 = fields.Char(
        string="Complemento",
    )
    number = fields.Char(
        string="Numero",
    )
    district = fields.Char(
        string="Bairro",
    )
    zip = fields.Char(
        string="CEP",
    )
    city = fields.Char(
        string="Cidade",
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Estado",
        domain="[('country_id.code', '=', 'BR')]",
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Pais",
        default=lambda self: self.env.ref("base.br", raise_if_not_found=False),
    )
    ibge_code = fields.Char(
        string="Codigo IBGE",
    )

    # Currency
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Moeda",
        default=lambda self: self.env.company.currency_id,
    )

    # Computed fields
    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )
    tempo_mercado = fields.Integer(
        string="Tempo de Mercado (anos)",
        compute="_compute_tempo_mercado",
        store=True,
    )
    full_address = fields.Char(
        string="Endereco Completo",
        compute="_compute_full_address",
    )
    cnpj_formatted = fields.Char(
        string="CNPJ Formatado",
        compute="_compute_cnpj_formatted",
    )

    # Relational fields
    partner_ids = fields.One2many(
        comodel_name="credit.partner",
        inverse_name="company_id",
        string="Socios",
    )
    analysis_ids = fields.One2many(
        comodel_name="credit.analysis",
        inverse_name="company_id",
        string="Consultas de Credito",
    )
    analysis_count = fields.Integer(
        string="Consultas",
        compute="_compute_analysis_count",
    )
    branch_ids = fields.One2many(
        comodel_name="credit.company.branch",
        inverse_name="company_id",
        string="Filiais",
    )

    _sql_constraints = [
        ("cnpj_unique", "unique(cnpj)", "O CNPJ deve ser unico!"),
    ]

    @api.depends("nome_fantasia", "razao_social")
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.nome_fantasia or record.razao_social

    @api.depends("data_fundacao")
    def _compute_tempo_mercado(self):
        today = fields.Date.today()
        for record in self:
            if record.data_fundacao:
                delta = today - record.data_fundacao
                record.tempo_mercado = delta.days // 365
            else:
                record.tempo_mercado = 0

    @api.depends(
        "street", "number", "street2", "district", "city", "state_id", "zip"
    )
    def _compute_full_address(self):
        for record in self:
            parts = []
            if record.street:
                addr = record.street
                if record.number:
                    addr += f", {record.number}"
                parts.append(addr)
            if record.street2:
                parts.append(record.street2)
            if record.district:
                parts.append(record.district)
            if record.city:
                city_state = record.city
                if record.state_id:
                    city_state += f" - {record.state_id.code}"
                parts.append(city_state)
            if record.zip:
                parts.append(f"CEP: {record.zip}")
            record.full_address = ", ".join(parts) if parts else ""

    @api.depends("cnpj")
    def _compute_cnpj_formatted(self):
        for record in self:
            if record.cnpj:
                cnpj_clean = re.sub(r"\D", "", record.cnpj)
                if len(cnpj_clean) == 14:
                    record.cnpj_formatted = (
                        f"{cnpj_clean[:2]}.{cnpj_clean[2:5]}."
                        f"{cnpj_clean[5:8]}/{cnpj_clean[8:12]}-{cnpj_clean[12:]}"
                    )
                else:
                    record.cnpj_formatted = record.cnpj
            else:
                record.cnpj_formatted = ""

    @api.depends("analysis_ids")
    def _compute_analysis_count(self):
        for record in self:
            record.analysis_count = len(record.analysis_ids)

    @api.constrains("cnpj")
    def _check_cnpj(self):
        for record in self:
            if record.cnpj:
                if not self._validate_cnpj(record.cnpj):
                    raise ValidationError(_("CNPJ invalido: %s") % record.cnpj)

    @api.model
    def _validate_cnpj(self, cnpj):
        """Validate CNPJ with check digit verification."""
        cnpj = re.sub(r"\D", "", cnpj)
        if len(cnpj) != 14:
            return False
        # Check for known invalid patterns
        if cnpj == cnpj[0] * 14:
            return False
        # First check digit
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum1 = sum(int(cnpj[i]) * weights1[i] for i in range(12))
        d1 = 11 - (sum1 % 11)
        d1 = 0 if d1 >= 10 else d1
        if int(cnpj[12]) != d1:
            return False
        # Second check digit
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum2 = sum(int(cnpj[i]) * weights2[i] for i in range(13))
        d2 = 11 - (sum2 % 11)
        d2 = 0 if d2 >= 10 else d2
        if int(cnpj[13]) != d2:
            return False
        return True

    @api.onchange("cnpj")
    def _onchange_cnpj(self):
        if self.cnpj:
            cnpj_clean = re.sub(r"\D", "", self.cnpj)
            if len(cnpj_clean) == 14:
                self.cnpj = (
                    f"{cnpj_clean[:2]}.{cnpj_clean[2:5]}."
                    f"{cnpj_clean[5:8]}/{cnpj_clean[8:12]}-{cnpj_clean[12:]}"
                )

    @api.onchange("zip")
    def _onchange_zip(self):
        if self.zip:
            zip_clean = re.sub(r"\D", "", self.zip)
            if len(zip_clean) == 8:
                self.zip = f"{zip_clean[:5]}-{zip_clean[5:]}"

    def action_view_analyses(self):
        """Open the list of credit analyses for this company."""
        self.ensure_one()
        return {
            "name": _("Consultas de Credito"),
            "type": "ir.actions.act_window",
            "res_model": "credit.analysis",
            "view_mode": "tree,form",
            "domain": [("company_id", "=", self.id)],
            "context": {"default_company_id": self.id},
        }

    def action_create_partner(self):
        """Create a res.partner from this company data."""
        self.ensure_one()
        partner_vals = {
            "name": self.nome_fantasia or self.razao_social,
            "company_type": "company",
            "vat": self.cnpj,
            "street": self.street,
            "street2": self.street2,
            "city": self.city,
            "state_id": self.state_id.id if self.state_id else False,
            "country_id": self.country_id.id if self.country_id else False,
            "zip": self.zip,
        }
        partner = self.env["res.partner"].create(partner_vals)
        self.partner_id = partner
        return {
            "name": _("Contato Criado"),
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "view_mode": "form",
            "res_id": partner.id,
        }

    def action_new_analysis(self):
        """Create a new credit analysis for this company."""
        self.ensure_one()
        return {
            "name": _("Nova Consulta de Credito"),
            "type": "ir.actions.act_window",
            "res_model": "credit.analysis",
            "view_mode": "form",
            "context": {
                "default_company_id": self.id,
            },
        }


class CreditCompanyBranch(models.Model):
    _name = "credit.company.branch"
    _description = "Filial da Empresa"
    _order = "cnpj"

    company_id = fields.Many2one(
        comodel_name="credit.company",
        string="Empresa Matriz",
        required=True,
        ondelete="cascade",
    )
    cnpj = fields.Char(
        string="CNPJ da Filial",
    )
    name = fields.Char(
        string="Nome",
    )
    street = fields.Char(
        string="Logradouro",
    )
    street2 = fields.Char(
        string="Complemento",
    )
    number = fields.Char(
        string="Numero",
    )
    district = fields.Char(
        string="Bairro",
    )
    zip = fields.Char(
        string="CEP",
    )
    city = fields.Char(
        string="Cidade",
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Estado",
        domain="[('country_id.code', '=', 'BR')]",
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="Pais",
        default=lambda self: self.env.ref("base.br", raise_if_not_found=False),
    )
