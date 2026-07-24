from odoo import fields, models


class ESocialTipoBeneficio(models.Model):
    _name = "l10n_br.esocial.tipo.beneficio"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 35 - Tipos de Benefícios"

    grupo = fields.Char()
    desc_grupo = fields.Char()
    permite_alt_grupo = fields.Char()


class ESocialInstEmprestimo(models.Model):
    _name = "l10n_br.esocial.inst.emprestimo"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 37 - Instituições Empréstimo Consignado"

    cnpj = fields.Char()


class ESocialRubricaPadrao(models.Model):
    _name = "l10n_br.esocial.rubrica.padrao"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 54 - Rubricas Padrão eSocial"

    nat_rubr = fields.Char()
    tp_rubr = fields.Char()
    cod_inc_cp = fields.Char()
    cod_inc_irrf = fields.Char()
    cod_inc_fgts = fields.Char()
    cod_inc_sind = fields.Char()
    rep_dsr = fields.Char()
    rep_13 = fields.Char()
    rep_ferias = fields.Char()
    rep_resc = fields.Char()
    rep_afast = fields.Char()
    fator_rubr = fields.Char()


class ESocialTipoDecisao(models.Model):
    _name = "l10n_br.esocial.tipo.decisao"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 59 - Tipo Decisão Judicial/Administrativa"

    tp_suspensao = fields.Char()


class ESocialCargo(models.Model):
    _name = "l10n_br.esocial.cargo"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 61 - Cargos"

    cod_grupo = fields.Char()
    cod_cbo = fields.Char()
    tp_trab = fields.Char()
