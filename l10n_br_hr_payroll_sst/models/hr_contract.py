# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

# Ordem de gravidade dos graus de insalubridade da NR-15.
ORDEM_GRAU = {"minimo": 1, "medio": 2, "maximo": 3}


class HrContract(models.Model):
    """Liga os adicionais de risco da folha ao laudo que os sustenta.

    Antes deste módulo, insalubridade e periculosidade eram caixas marcadas à
    mão no contrato. Em fiscalização ou reclamatória, quem sustenta o pagamento
    é o laudo, e é ele que também sustenta o S-2240: contrato e laudo divergindo
    em silêncio é o pior dos mundos. Aqui os campos passam a ser calculados a
    partir do risco vigente, mas continuam editáveis, porque acordo coletivo e
    decisão judicial podem obrigar a pagar o que o laudo não aponta. O que não
    se admite é a divergência passar despercebida.
    """

    _inherit = "hr.contract"

    l10n_br_periculosidade = fields.Boolean(
        compute="_compute_l10n_br_adicionais_sst",
        store=True,
        readonly=False,
    )
    l10n_br_insalubridade = fields.Boolean(
        compute="_compute_l10n_br_adicionais_sst",
        store=True,
        readonly=False,
    )
    l10n_br_grau_insalubridade = fields.Selection(
        compute="_compute_l10n_br_adicionais_sst",
        store=True,
        readonly=False,
    )
    l10n_br_sst_insalubridade_laudo = fields.Boolean(
        string="Insalubridade no Laudo",
        compute="_compute_l10n_br_sst_laudo",
    )
    l10n_br_sst_grau_laudo = fields.Selection(
        selection=lambda self: self.env["l10n_br.sst.risco"]
        ._fields["grau_insalubridade"]
        .selection,
        string="Grau no Laudo",
        compute="_compute_l10n_br_sst_laudo",
    )
    l10n_br_sst_periculosidade_laudo = fields.Boolean(
        string="Periculosidade no Laudo",
        compute="_compute_l10n_br_sst_laudo",
    )
    l10n_br_sst_divergencia = fields.Char(
        string="Divergência com o Laudo",
        compute="_compute_l10n_br_sst_laudo",
        help="Preenchido quando o contrato paga adicional que o laudo não "
        "aponta, ou deixa de pagar o que ele aponta.",
    )
    l10n_br_sst_justificativa = fields.Char(
        string="Justificativa da Divergência",
        help="Convenção coletiva, decisão judicial ou outro fundamento para o "
        "contrato divergir do laudo.",
    )
    l10n_br_sst_aliquota_gilrat = fields.Float(
        string="GILRAT Adicional (%)",
        compute="_compute_l10n_br_sst_aliquota_gilrat",
        store=True,
        digits=(5, 2),
        help="Alíquota adicional de financiamento da aposentadoria especial: "
        "12% para 15 anos, 9% para 20 anos e 6% para 25 anos de exposição.",
    )

    def _l10n_br_sst_adicionais_do_laudo(self, data=None):
        """Insalubridade, grau e periculosidade apurados no risco vigente."""
        self.ensure_one()
        riscos = self._l10n_br_sst_riscos_vigentes(data)
        insalubres = riscos.filtered("insalubridade")
        graus = [g for g in insalubres.mapped("grau_insalubridade") if g in ORDEM_GRAU]
        grau = max(graus, key=lambda g: ORDEM_GRAU[g]) if graus else False
        return {
            "insalubridade": bool(insalubres),
            "grau": grau,
            "periculosidade": bool(riscos.filtered("periculosidade")),
        }

    @api.depends(
        "l10n_br_sst_ambiente_id",
        "l10n_br_sst_ambiente_id.risco_ids",
        "l10n_br_sst_ambiente_id.risco_ids.insalubridade",
        "l10n_br_sst_ambiente_id.risco_ids.grau_insalubridade",
        "l10n_br_sst_ambiente_id.risco_ids.periculosidade",
        "job_id",
    )
    def _compute_l10n_br_adicionais_sst(self):
        """Deriva os adicionais do laudo, sem sobrescrever ajuste manual.

        Contrato sem ambiente mantém o que estiver lá: quem ainda não implantou
        o inventário de riscos não pode perder o adicional que já pagava.
        """
        for rec in self:
            if not rec.l10n_br_sst_ambiente_id:
                rec.l10n_br_periculosidade = rec.l10n_br_periculosidade
                rec.l10n_br_insalubridade = rec.l10n_br_insalubridade
                rec.l10n_br_grau_insalubridade = rec.l10n_br_grau_insalubridade
                continue
            laudo = rec._l10n_br_sst_adicionais_do_laudo()
            if laudo["insalubridade"] and laudo["periculosidade"]:
                # Súmula 364 do TST: não acumulam. Fica a insalubridade, e a
                # divergência aparece para decisão humana.
                laudo["periculosidade"] = False
            rec.l10n_br_insalubridade = laudo["insalubridade"]
            rec.l10n_br_grau_insalubridade = laudo["grau"]
            rec.l10n_br_periculosidade = laudo["periculosidade"]

    @api.depends(
        "l10n_br_insalubridade",
        "l10n_br_grau_insalubridade",
        "l10n_br_periculosidade",
        "l10n_br_sst_ambiente_id",
        "job_id",
    )
    def _compute_l10n_br_sst_laudo(self):
        for rec in self:
            laudo = rec._l10n_br_sst_adicionais_do_laudo()
            rec.l10n_br_sst_insalubridade_laudo = laudo["insalubridade"]
            rec.l10n_br_sst_grau_laudo = laudo["grau"]
            rec.l10n_br_sst_periculosidade_laudo = laudo["periculosidade"]
            divergencias = []
            if rec.l10n_br_insalubridade != laudo["insalubridade"]:
                divergencias.append(
                    _("insalubridade paga: %(contrato)s; laudo: %(laudo)s")
                    % {
                        "contrato": _("sim") if rec.l10n_br_insalubridade else _("não"),
                        "laudo": _("sim") if laudo["insalubridade"] else _("não"),
                    }
                )
            elif (
                rec.l10n_br_insalubridade
                and rec.l10n_br_grau_insalubridade != laudo["grau"]
            ):
                divergencias.append(_("grau de insalubridade divergente do laudo"))
            if rec.l10n_br_periculosidade != laudo["periculosidade"]:
                divergencias.append(
                    _("periculosidade paga: %(contrato)s; laudo: %(laudo)s")
                    % {
                        "contrato": _("sim")
                        if rec.l10n_br_periculosidade
                        else _("não"),
                        "laudo": _("sim") if laudo["periculosidade"] else _("não"),
                    }
                )
            rec.l10n_br_sst_divergencia = "; ".join(divergencias)

    @api.depends(
        "l10n_br_sst_ambiente_id",
        "l10n_br_sst_ambiente_id.risco_ids",
        "l10n_br_sst_ambiente_id.risco_ids.financiamento_aposent_id",
        "job_id",
    )
    def _compute_l10n_br_sst_aliquota_gilrat(self):
        for rec in self:
            riscos = rec._l10n_br_sst_riscos_vigentes()
            rec.l10n_br_sst_aliquota_gilrat = riscos._aliquota_gilrat_adicional()
