from odoo import fields, models


class MonetaryIndex(models.Model):
    _inherit = "monetary.index"

    bcb_sgs_code = fields.Char(
        string="Série SGS (BCB)",
        help="Código da série no Sistema Gerenciador de Séries Temporais do "
        "Banco Central (ex.: 433 IPCA, 188 INPC, 189 IGP-M, 4390 SELIC). "
        "Com o código preenchido, as taxas são buscadas na API do Banco Central.",
    )
