# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ESocialCompatCategLotacao(models.Model):
    _name = "l10n_br.esocial.compat.categ.lotacao"
    _description = "eSocial Tab 11 - Compatibilidade Categoria/ClassTrib/Lotação"
    _order = "cod_categ, class_trib"

    cod_categ = fields.Char(required=True, index=True)
    class_trib = fields.Char()
    dt_inicio = fields.Date()
    dt_fim = fields.Date()
    n_class_trib = fields.Char()
    cooperativa = fields.Char()
    tp_lotacao = fields.Char()
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    @api.depends("cod_categ", "class_trib", "tp_lotacao")
    def _compute_name(self):
        for rec in self:
            rec.name = (
                f"Cat {rec.cod_categ or ''}"
                f" - ClassTrib {rec.class_trib or ''}"
                f" - Lot {rec.tp_lotacao or ''}"
            )


class ESocialLotacaoRef(models.Model):
    _name = "l10n_br.esocial.lotacao.ref"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 64 - Lotações Tributárias (Referência)"

    tp_lotacao = fields.Char()
    tp_insc = fields.Char()
    nr_insc = fields.Char()
    fpas = fields.Char()
    cod_tercs = fields.Char()


class ESocialProcessoFap(models.Model):
    _name = "l10n_br.esocial.processo.fap"
    _description = "eSocial Tab 77 - Processo FAP"
    _order = "processo"

    processo = fields.Char(required=True, index=True)
    nr_inscricao = fields.Char(required=True)
    dt_inicio = fields.Date()
    dt_fim = fields.Date()
    active = fields.Boolean(default=True)
    name = fields.Char(compute="_compute_name", store=True)

    @api.depends("processo", "nr_inscricao")
    def _compute_name(self):
        for rec in self:
            rec.name = f"Proc {rec.processo or ''}" f" - {rec.nr_inscricao or ''}"


class ESocialCnaeMei(models.Model):
    _name = "l10n_br.esocial.cnae.mei"
    _inherit = ["l10n_br.esocial.tabela.mixin"]
    _description = "eSocial Tab 81 - CNAE MEI Web"

    cod_cnae = fields.Char()
