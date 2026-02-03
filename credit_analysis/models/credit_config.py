# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CreditConfig(models.Model):
    _name = "credit.config"
    _description = "Configuracao de Analise de Credito"

    name = fields.Char(
        string="Nome",
        required=True,
        default="Configuracao Padrao",
    )
    active = fields.Boolean(
        default=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Empresa",
        default=lambda self: self.env.company,
    )

    # Score ranges
    score_very_high_min = fields.Integer(
        string="Score Muito Alto - Minimo",
        default=0,
    )
    score_very_high_max = fields.Integer(
        string="Score Muito Alto - Maximo",
        default=200,
    )
    score_high_min = fields.Integer(
        string="Score Alto - Minimo",
        default=201,
    )
    score_high_max = fields.Integer(
        string="Score Alto - Maximo",
        default=400,
    )
    score_medium_min = fields.Integer(
        string="Score Medio - Minimo",
        default=401,
    )
    score_medium_max = fields.Integer(
        string="Score Medio - Maximo",
        default=600,
    )
    score_low_min = fields.Integer(
        string="Score Baixo - Minimo",
        default=601,
    )
    score_low_max = fields.Integer(
        string="Score Baixo - Maximo",
        default=800,
    )
    score_very_low_min = fields.Integer(
        string="Score Muito Baixo - Minimo",
        default=801,
    )
    score_very_low_max = fields.Integer(
        string="Score Muito Baixo - Maximo",
        default=1000,
    )

    # Default probabilities
    prob_very_high = fields.Float(
        string="Prob. Inadimplencia - Muito Alto (%)",
        default=50.0,
    )
    prob_high = fields.Float(
        string="Prob. Inadimplencia - Alto (%)",
        default=35.0,
    )
    prob_medium = fields.Float(
        string="Prob. Inadimplencia - Medio (%)",
        default=20.0,
    )
    prob_low = fields.Float(
        string="Prob. Inadimplencia - Baixo (%)",
        default=10.0,
    )
    prob_very_low = fields.Float(
        string="Prob. Inadimplencia - Muito Baixo (%)",
        default=3.0,
    )

    # Credit limit factors
    limite_factor_very_low = fields.Float(
        string="Fator Limite - Muito Baixo",
        default=0.10,
        help="Multiplicador do faturamento para calculo do limite",
    )
    limite_factor_low = fields.Float(
        string="Fator Limite - Baixo",
        default=0.08,
    )
    limite_factor_medium = fields.Float(
        string="Fator Limite - Medio",
        default=0.05,
    )
    limite_factor_high = fields.Float(
        string="Fator Limite - Alto",
        default=0.03,
    )
    limite_factor_very_high = fields.Float(
        string="Fator Limite - Muito Alto",
        default=0.01,
    )

    # Report settings
    report_disclaimer = fields.Text(
        string="Disclaimer do Relatorio",
        default="""CONFIDENCIAL - Este documento contem informacoes confidenciais
destinadas exclusivamente ao uso interno da empresa. A reproducao,
distribuicao ou divulgacao sem autorizacao expressa e proibida.
As informacoes aqui contidas sao baseadas em dados disponiveis no
momento da consulta e nao constituem garantia de credito.""",
    )
    report_watermark_enabled = fields.Boolean(
        string="Habilitar Marca d'Agua",
        default=True,
    )
    report_watermark_text = fields.Char(
        string="Texto Marca d'Agua",
        default="CONFIDENCIAL",
    )

    _sql_constraints = [
        (
            "company_unique",
            "unique(company_id)",
            "Ja existe uma configuracao para esta empresa!",
        ),
    ]

    @classmethod
    def get_config(cls, env):
        """Get the configuration for the current company."""
        config = env["credit.config"].search(
            [("company_id", "=", env.company.id)], limit=1
        )
        if not config:
            config = env["credit.config"].search(
                [("company_id", "=", False)], limit=1
            )
        return config
