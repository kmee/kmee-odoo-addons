# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CreditSubject(models.Model):
    _name = "credit.subject"
    _description = "Sujeito para Consulta de Credito"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    # Subject Type
    subject_type = fields.Selection(
        selection=[
            ("pj", "Pessoa Juridica"),
            ("pf", "Pessoa Fisica"),
        ],
        string="Tipo de Pessoa",
        default="pj",
        required=True,
        tracking=True,
    )

    # Document fields
    document = fields.Char(
        string="Documento",
        required=True,
        index="btree",
        tracking=True,
        help="CPF para Pessoa Fisica ou CNPJ para Pessoa Juridica",
    )
    document_formatted = fields.Char(
        string="Documento Formatado",
        compute="_compute_document_formatted",
    )

    # Common fields
    name = fields.Char(
        string="Nome/Razao Social",
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

    # PF specific fields
    data_nascimento = fields.Date(
        string="Data de Nascimento",
        tracking=True,
    )
    sexo = fields.Selection(
        selection=[
            ("m", "Masculino"),
            ("f", "Feminino"),
            ("o", "Outro"),
        ],
        string="Sexo",
    )
    estado_civil = fields.Selection(
        selection=[
            ("solteiro", "Solteiro(a)"),
            ("casado", "Casado(a)"),
            ("divorciado", "Divorciado(a)"),
            ("viuvo", "Viuvo(a)"),
            ("separado", "Separado(a)"),
            ("uniao_estavel", "Uniao Estavel"),
        ],
        string="Estado Civil",
    )
    rg = fields.Char(
        string="RG",
    )
    rg_orgao_emissor = fields.Char(
        string="Orgao Emissor RG",
    )
    rg_uf_id = fields.Many2one(
        comodel_name="res.country.state",
        string="UF RG",
        domain="[('country_id.code', '=', 'BR')]",
    )
    nome_mae = fields.Char(
        string="Nome da Mae",
    )
    nome_pai = fields.Char(
        string="Nome do Pai",
    )
    profissao = fields.Char(
        string="Profissao",
    )
    renda_mensal = fields.Monetary(
        string="Renda Mensal",
        currency_field="currency_id",
    )
    empregador = fields.Char(
        string="Empregador",
    )
    data_admissao = fields.Date(
        string="Data de Admissao",
    )

    # PJ specific fields (Cadastral data F03)
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
        relation="credit_subject_cnae_secundario_rel",
        column1="subject_id",
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
            ("regular", "Regular"),
            ("pendente", "Pendente"),
            ("cancelado", "Cancelado"),
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

    # Contact info
    phone = fields.Char(
        string="Telefone",
    )
    mobile = fields.Char(
        string="Celular",
    )
    email = fields.Char(
        string="E-mail",
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
    tempo_atividade = fields.Integer(
        string="Tempo de Atividade (anos)",
        compute="_compute_tempo_atividade",
        store=True,
    )
    idade = fields.Integer(
        string="Idade",
        compute="_compute_idade",
    )
    full_address = fields.Char(
        string="Endereco Completo",
        compute="_compute_full_address",
    )
    is_pf = fields.Boolean(
        string="E Pessoa Fisica",
        compute="_compute_is_pf",
        store=True,
    )
    is_pj = fields.Boolean(
        string="E Pessoa Juridica",
        compute="_compute_is_pf",
        store=True,
    )

    # Relational fields
    partner_ids = fields.One2many(
        comodel_name="credit.partner",
        inverse_name="subject_id",
        string="Socios",
    )
    analysis_ids = fields.One2many(
        comodel_name="credit.analysis",
        inverse_name="subject_id",
        string="Consultas de Credito",
    )
    analysis_count = fields.Integer(
        string="Consultas",
        compute="_compute_analysis_count",
    )
    branch_ids = fields.One2many(
        comodel_name="credit.subject.branch",
        inverse_name="subject_id",
        string="Filiais",
    )

    _sql_constraints = [
        (
            "document_unique",
            "unique(document)",
            "O documento (CPF/CNPJ) deve ser unico!",
        ),
    ]

    @api.depends("subject_type")
    def _compute_is_pf(self):
        for record in self:
            record.is_pf = record.subject_type == "pf"
            record.is_pj = record.subject_type == "pj"

    @api.depends("nome_fantasia", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.nome_fantasia or record.name

    @api.depends("data_fundacao", "data_inicio_atividade", "subject_type")
    def _compute_tempo_atividade(self):
        today = fields.Date.today()
        for record in self:
            data_ref = record.data_fundacao or record.data_inicio_atividade
            if data_ref:
                delta = today - data_ref
                record.tempo_atividade = delta.days // 365
            else:
                record.tempo_atividade = 0

    @api.depends("data_nascimento")
    def _compute_idade(self):
        today = fields.Date.today()
        for record in self:
            if record.data_nascimento:
                delta = today - record.data_nascimento
                record.idade = delta.days // 365
            else:
                record.idade = 0

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

    @api.depends("document", "subject_type")
    def _compute_document_formatted(self):
        for record in self:
            if record.document:
                doc_clean = re.sub(r"\D", "", record.document)
                if record.subject_type == "pf" and len(doc_clean) == 11:
                    record.document_formatted = (
                        f"{doc_clean[:3]}.{doc_clean[3:6]}."
                        f"{doc_clean[6:9]}-{doc_clean[9:]}"
                    )
                elif record.subject_type == "pj" and len(doc_clean) == 14:
                    record.document_formatted = (
                        f"{doc_clean[:2]}.{doc_clean[2:5]}."
                        f"{doc_clean[5:8]}/{doc_clean[8:12]}-{doc_clean[12:]}"
                    )
                else:
                    record.document_formatted = record.document
            else:
                record.document_formatted = ""

    @api.depends("analysis_ids")
    def _compute_analysis_count(self):
        for record in self:
            record.analysis_count = len(record.analysis_ids)

    @api.constrains("document", "subject_type")
    def _check_document(self):
        for record in self:
            if record.document:
                if record.subject_type == "pf":
                    if not self._validate_cpf(record.document):
                        raise ValidationError(
                            _("CPF invalido: %s") % record.document
                        )
                else:
                    if not self._validate_cnpj(record.document):
                        raise ValidationError(
                            _("CNPJ invalido: %s") % record.document
                        )

    @api.model
    def _validate_cpf(self, cpf):
        """Validate CPF with check digit verification."""
        cpf = re.sub(r"\D", "", cpf)
        if len(cpf) != 11:
            return False
        # Check for known invalid patterns
        if cpf == cpf[0] * 11:
            return False
        # First check digit
        sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        d1 = 11 - (sum1 % 11)
        d1 = 0 if d1 >= 10 else d1
        if int(cpf[9]) != d1:
            return False
        # Second check digit
        sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        d2 = 11 - (sum2 % 11)
        d2 = 0 if d2 >= 10 else d2
        if int(cpf[10]) != d2:
            return False
        return True

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

    @api.onchange("document", "subject_type")
    def _onchange_document(self):
        if self.document:
            doc_clean = re.sub(r"\D", "", self.document)
            if self.subject_type == "pf" and len(doc_clean) == 11:
                self.document = (
                    f"{doc_clean[:3]}.{doc_clean[3:6]}."
                    f"{doc_clean[6:9]}-{doc_clean[9:]}"
                )
            elif self.subject_type == "pj" and len(doc_clean) == 14:
                self.document = (
                    f"{doc_clean[:2]}.{doc_clean[2:5]}."
                    f"{doc_clean[5:8]}/{doc_clean[8:12]}-{doc_clean[12:]}"
                )

    @api.onchange("zip")
    def _onchange_zip(self):
        if self.zip:
            zip_clean = re.sub(r"\D", "", self.zip)
            if len(zip_clean) == 8:
                self.zip = f"{zip_clean[:5]}-{zip_clean[5:]}"

    def action_view_analyses(self):
        """Open the list of credit analyses for this subject."""
        self.ensure_one()
        return {
            "name": _("Consultas de Credito"),
            "type": "ir.actions.act_window",
            "res_model": "credit.analysis",
            "view_mode": "tree,form",
            "domain": [("subject_id", "=", self.id)],
            "context": {"default_subject_id": self.id},
        }

    def action_create_partner(self):
        """Create a res.partner from this subject data."""
        self.ensure_one()
        partner_vals = {
            "name": self.nome_fantasia or self.name,
            "company_type": "company" if self.subject_type == "pj" else "person",
            "vat": self.document,
            "street": self.street,
            "street2": self.street2,
            "city": self.city,
            "state_id": self.state_id.id if self.state_id else False,
            "country_id": self.country_id.id if self.country_id else False,
            "zip": self.zip,
            "phone": self.phone,
            "mobile": self.mobile,
            "email": self.email,
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
        """Create a new credit analysis for this subject."""
        self.ensure_one()
        return {
            "name": _("Nova Consulta de Credito"),
            "type": "ir.actions.act_window",
            "res_model": "credit.analysis",
            "view_mode": "form",
            "context": {
                "default_subject_id": self.id,
            },
        }


class CreditSubjectBranch(models.Model):
    _name = "credit.subject.branch"
    _description = "Filial da Empresa"
    _order = "document"

    subject_id = fields.Many2one(
        comodel_name="credit.subject",
        string="Empresa Matriz",
        required=True,
        ondelete="cascade",
    )
    document = fields.Char(
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
