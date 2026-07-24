# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ESocialReceitaTotalizador(models.Model):
    _name = "l10n_br.esocial.receita.totalizador"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 78 - Receita dos Totalizadores"


class ESocialValorContribPrev(models.Model):
    _name = "l10n_br.esocial.valor.contrib.prev"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 79 - Tipo Valor Contribuição Previdenciária"


class ESocialValorIrrfTotalizador(models.Model):
    _name = "l10n_br.esocial.valor.irrf.totalizador"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 80 - Tipo Valor IRRF Totalizadores"


class ESocialBaseFgts(models.Model):
    _name = "l10n_br.esocial.base.fgts"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 82 - Bases de Cálculo FGTS"


class ESocialDepositoFgts(models.Model):
    _name = "l10n_br.esocial.deposito.fgts"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 83 - Tipos de Depósito FGTS"
