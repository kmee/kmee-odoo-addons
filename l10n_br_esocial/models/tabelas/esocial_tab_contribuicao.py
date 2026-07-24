# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ESocialFpasTerceiros(models.Model):
    _name = "l10n_br.esocial.fpas.terceiros"
    _description = "eSocial Tab 04 - FPAS/Terceiros"
    _order = "cod_fpas"

    cod_fpas = fields.Char(required=True, index=True)
    ind_coop = fields.Char()
    dt_inicio = fields.Date()
    dt_fim = fields.Date()
    class_trib = fields.Char()
    cod_terc = fields.Char()
    aliq_terc = fields.Char()
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    @api.depends("cod_fpas")
    def _compute_name(self):
        for rec in self:
            rec.name = f"[{rec.cod_fpas}] FPAS {rec.cod_fpas}" if rec.cod_fpas else ""


class ESocialIncidenciaIrrf(models.Model):
    _name = "l10n_br.esocial.incidencia.irrf"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 21 - Incidência Tributária IRRF"


class ESocialCompatFpas(models.Model):
    _name = "l10n_br.esocial.compat.fpas"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 24 - Compatibilidade FPAS/Classificação Tributária"

    nome = fields.Char(required=False)
    class_trib_list = fields.Char(string="Classificações Tributárias")


class ESocialTribExterior(models.Model):
    _name = "l10n_br.esocial.trib.exterior"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 30 - Tributação Beneficiários Exterior"


class ESocialCodigoTerceiro(models.Model):
    _name = "l10n_br.esocial.codigo.terceiro"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 51 - Códigos de Terceiro"

    obriga = fields.Char()


class ESocialFaixaInss(models.Model):
    _name = "l10n_br.esocial.faixa.inss"
    _description = "eSocial Tab 57 - Contribuição Previdenciária Empregado"
    _order = "dt_inicio, inf_sal_cont"

    inf_sal_cont = fields.Char(required=True)
    sup_sal_cont = fields.Char(required=True)
    dt_inicio = fields.Date()
    dt_fim = fields.Date()
    aliquota = fields.Char()
    parcela_deduzir = fields.Char()
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    @api.depends("inf_sal_cont", "sup_sal_cont", "aliquota")
    def _compute_name(self):
        for rec in self:
            if rec.inf_sal_cont and rec.sup_sal_cont:
                rec.name = (
                    f"R$ {rec.inf_sal_cont} a R$ {rec.sup_sal_cont}"
                    f" - {rec.aliquota}%"
                )
            else:
                rec.name = ""


class ESocialFaixaIrrf(models.Model):
    _name = "l10n_br.esocial.faixa.irrf"
    _description = "eSocial Tab 58 - Retenção IRRF"
    _order = "dt_inicio, inf_base_calc"

    inf_base_calc = fields.Char(required=True)
    sup_base_calc = fields.Char(required=True)
    dt_inicio = fields.Date()
    dt_fim = fields.Date()
    aliquota = fields.Char()
    parcela_deduzir = fields.Char()
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    @api.depends("inf_base_calc", "sup_base_calc", "aliquota")
    def _compute_name(self):
        for rec in self:
            if rec.inf_base_calc and rec.sup_base_calc:
                rec.name = (
                    f"R$ {rec.inf_base_calc} a R$ {rec.sup_base_calc}"
                    f" - {rec.aliquota}%"
                )
            else:
                rec.name = ""


class ESocialFaixaSalFamilia(models.Model):
    _name = "l10n_br.esocial.faixa.sal.familia"
    _description = "eSocial Tab 65 - Salário Família"
    _order = "dt_inicio, inf_base_calc"

    inf_base_calc = fields.Char(required=True)
    sup_base_calc = fields.Char(required=True)
    dt_inicio = fields.Date()
    dt_fim = fields.Date()
    valor = fields.Char()
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    @api.depends("inf_base_calc", "sup_base_calc", "valor")
    def _compute_name(self):
        for rec in self:
            if rec.inf_base_calc and rec.sup_base_calc:
                rec.name = (
                    f"R$ {rec.inf_base_calc} a R$ {rec.sup_base_calc}"
                    f" → R$ {rec.valor}"
                )
            else:
                rec.name = ""


class ESocialDescricaoFpas(models.Model):
    _name = "l10n_br.esocial.descricao.fpas"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 85 - Descrição FPAS"


class ESocialTetoVerdeAmarela(models.Model):
    _name = "l10n_br.esocial.teto.verde.amarela"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 86 - Teto Isenção Programa Verde e Amarela"
