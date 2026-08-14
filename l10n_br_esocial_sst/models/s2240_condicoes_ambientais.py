# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_br_hr_sst.models.sst_dominios import COD_AGENTE_NOCIVO_AUSENCIA


class ESocialS2240(models.Model):
    """S-2240 - Condições Ambientais do Trabalho, Agentes Nocivos.

    O evento é por trabalhador e tem histórico: cada mudança de risco gera um
    novo evento com nova data de início, e não a sobrescrita do anterior. É
    dele que o INSS monta o PPP eletrônico, de modo que erro aqui atinge o
    direito previdenciário do trabalhador, não só o caixa da empresa.
    """

    _name = "l10n_br.esocial.s2240"
    _inherit = "l10n_br.esocial.base.sst"
    _description = "eSocial S-2240 - Condições Ambientais do Trabalho"
    _order = "dt_ini_condicao desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    contract_id = fields.Many2one(
        "hr.contract",
        string="Contrato",
        required=True,
        ondelete="cascade",
    )
    ambiente_id = fields.Many2one(
        "l10n_br.sst.ambiente",
        string="Ambiente",
        required=True,
    )
    laudo_id = fields.Many2one(
        "l10n_br.sst.laudo",
        string="Laudo",
        help="Laudo que originou este evento.",
    )
    dt_ini_condicao = fields.Date(
        string="Início da Condição",
        required=True,
        default=fields.Date.context_today,
    )
    dt_fim_condicao = fields.Date(
        string="Fim da Condição",
    )
    dsc_ativ_des = fields.Text(
        string="Descrição das Atividades",
        required=True,
    )
    risco_ids = fields.Many2many(
        "l10n_br.sst.risco",
        string="Fatores de Risco",
        required=True,
    )
    responsavel_ids = fields.Many2many(
        "l10n_br.sst.responsavel",
        string="Responsáveis pelos Registros Ambientais",
        required=True,
    )
    obs_compl = fields.Text(string="Observação Complementar")

    @api.depends("employee_id", "dt_ini_condicao")
    def _compute_name(self):
        for rec in self:
            partes = [
                rec.employee_id.name,
                rec.dt_ini_condicao and str(rec.dt_ini_condicao),
            ]
            rec.name = " - ".join(p for p in partes if p)

    def _get_event_type(self):
        return "S-2240"

    # ── Montagem do grupo agNoc ─────────────────────────────────────────────

    def _epis_do_risco(self, risco):
        """Entregas de EPI válidas na data da condição que cobrem o risco."""
        self.ensure_one()
        return self.employee_id._l10n_br_sst_epis_do_risco(risco, self.dt_ini_condicao)

    def _to_ag_noc(self, risco):
        """Monta um grupo agNoc a partir do fator de risco e das entregas de EPI."""
        self.ensure_one()
        dados = {"cod_ag_noc": risco.agente_nocivo_id.codigo}
        if risco.descricao:
            dados["dsc_ag_noc"] = risco.descricao
        if risco.ausencia_de_risco:
            # Sem agente nocivo o leiaute só admite ausência de proteção.
            dados["utiliz_epc"] = 0
            dados["utiliz_epi"] = 0
            return dados

        if risco.tp_aval:
            dados["tp_aval"] = int(risco.tp_aval)
        if risco.intensidade:
            dados["int_conc"] = "%.4f" % risco.intensidade
        if risco.limite_tolerancia:
            dados["lim_tol"] = "%.4f" % risco.limite_tolerancia
        if risco.un_med:
            dados["un_med"] = int(risco.un_med)
        if risco.tecnica_medicao:
            dados["tec_medicao"] = risco.tecnica_medicao
        if risco.nr_proc_jud:
            dados["nr_proc_jud"] = risco.nr_proc_jud

        dados["utiliz_epc"] = int(risco.utiliz_epc or "0")
        if risco.utiliz_epc == "2":
            dados["efic_epc"] = risco.efic_epc or "N"

        entregas = self._epis_do_risco(risco)
        utiliz_epi = int(risco.utiliz_epi or "0")
        dados["utiliz_epi"] = utiliz_epi
        if utiliz_epi != 2:
            return dados

        dados["efic_epi"] = risco.efic_epi or "N"
        cas = entregas.mapped("l10n_br_sst_ca_id")
        if cas:
            dados["epi"] = [{"doc_aval": ca.numero} for ca in cas]
            principal = cas[0]
            dados.update(
                {
                    "med_protecao": principal.med_protecao or "N",
                    "cond_functo": principal.cond_functo or "N",
                    "uso_inint": principal.uso_inint or "N",
                    "prz_valid": principal.prz_valid or "N",
                    "periodic_troca": principal.periodic_troca or "N",
                    "higienizacao": principal.higienizacao or "N",
                }
            )
        return dados

    # ── Validações antes do envio (RS-17) ───────────────────────────────────

    def _validar_antes_do_envio(self):
        """Reproduz as regras do S-2240 que só apareceriam na rejeição.

        Descobrir a inconsistência no retorno do eSocial custa o prazo do dia
        15; por isso as mesmas regras rodam aqui, antes de gerar o XML.
        """
        for rec in self:
            if not rec.risco_ids:
                raise UserError(
                    _(
                        "S-2240 de %(nome)s: informe ao menos um fator de "
                        "risco. Ausência de exposição se declara com o código "
                        "%(codigo)s, e não com a omissão do grupo."
                    )
                    % {
                        "nome": rec.employee_id.name,
                        "codigo": COD_AGENTE_NOCIVO_AUSENCIA,
                    }
                )
            if not rec.responsavel_ids:
                raise UserError(
                    _(
                        "S-2240 de %(nome)s: o responsável pelos registros "
                        "ambientais é obrigatório."
                    )
                    % {"nome": rec.employee_id.name}
                )
            if len(rec.risco_ids) > 1 and any(
                risco.ausencia_de_risco for risco in rec.risco_ids
            ):
                raise UserError(
                    _(
                        "S-2240 de %(nome)s: o código de ausência de agente "
                        "nocivo não convive com outros fatores de risco no "
                        "mesmo evento."
                    )
                    % {"nome": rec.employee_id.name}
                )
            for risco in rec.risco_ids:
                rec._validar_risco(risco)

    def _validar_risco(self, risco):
        self.ensure_one()
        nome = self.employee_id.name
        agente = risco.agente_nocivo_id.name
        if risco.ausencia_de_risco:
            if risco.utiliz_epc not in (False, "0") or risco.utiliz_epi not in (
                False,
                "0",
            ):
                raise UserError(
                    _(
                        "S-2240 de %(nome)s: com ausência de agente nocivo, a "
                        "utilização de EPC e de EPI deve ser 'não se aplica'."
                    )
                    % {"nome": nome}
                )
            return
        if risco.utiliz_epc == "2" and not risco.efic_epc:
            raise UserError(
                _(
                    "S-2240 de %(nome)s, agente %(agente)s: informe se o EPC "
                    "implementado é eficaz."
                )
                % {"nome": nome, "agente": agente}
            )
        if risco.utiliz_epi != "2":
            return
        if not risco.efic_epi:
            raise UserError(
                _(
                    "S-2240 de %(nome)s, agente %(agente)s: informe se o EPI "
                    "utilizado é eficaz."
                )
                % {"nome": nome, "agente": agente}
            )
        entregas = self._epis_do_risco(risco)
        if not entregas.mapped("l10n_br_sst_ca_id"):
            raise UserError(
                _(
                    "S-2240 de %(nome)s, agente %(agente)s: o evento declara "
                    "uso de EPI, mas não há entrega válida com Certificado de "
                    "Aprovação em %(data)s. Registre a entrega ou corrija a "
                    "utilização de EPI no fator de risco."
                )
                % {
                    "nome": nome,
                    "agente": agente,
                    "data": self.dt_ini_condicao,
                }
            )

    def action_validar(self):
        self._validar_antes_do_envio()
        return True

    def action_gerar_evento(self):
        self._validar_antes_do_envio()
        return super().action_gerar_evento()

    def _to_esociallib_dict(self):
        self.ensure_one()
        self._validar_antes_do_envio()
        dados = self._get_dados_comuns()
        dados.update(
            {
                "dt_ini_condicao": str(self.dt_ini_condicao),
                "info_amb": [self.ambiente_id._to_info_amb()],
                "dsc_ativ_des": self.dsc_ativ_des,
                "ag_noc": [self._to_ag_noc(risco) for risco in self.risco_ids],
                "resp_reg": [resp._to_resp_reg() for resp in self.responsavel_ids],
            }
        )
        if self.dt_fim_condicao:
            dados["dt_fim_condicao"] = str(self.dt_fim_condicao)
        if self.obs_compl:
            dados["obs_compl"] = self.obs_compl
        return dados

    # ── Geração a partir do contrato e em massa ─────────────────────────────

    @api.model
    def gerar_para_contrato(self, contract, data=None, laudo=None):
        """Cria o S-2240 de um contrato a partir dos riscos vigentes.

        Args:
            contract: recordset de ``hr.contract`` (um registro).
            data: data de início da condição; ``None`` usa hoje.
            laudo: laudo de origem, quando a geração parte dele.

        Returns:
            O intermediário criado, ou recordset vazio quando o contrato não
            tem ambiente ou não tem risco vigente.
        """
        contract.ensure_one()
        data = fields.Date.to_date(data) or fields.Date.context_today(contract)
        riscos = contract._l10n_br_sst_riscos_vigentes(data)
        if not contract.l10n_br_sst_ambiente_id or not riscos:
            return self.browse()
        responsaveis = riscos.mapped("laudo_id.responsavel_id")
        if not responsaveis and laudo:
            responsaveis = laudo.responsavel_id
        return self.create(
            {
                "company_id": contract.company_id.id,
                "employee_id": contract.employee_id.id,
                "contract_id": contract.id,
                "ambiente_id": contract.l10n_br_sst_ambiente_id.id,
                "laudo_id": laudo.id if laudo else riscos[:1].laudo_id.id,
                "dt_ini_condicao": data,
                "dsc_ativ_des": contract._l10n_br_sst_descricao_atividade(),
                "risco_ids": [(6, 0, riscos.ids)],
                "responsavel_ids": [(6, 0, responsaveis.ids)],
            }
        )

    @api.model
    def gerar_em_massa(self, contracts, data=None, laudo=None):
        """Gera o S-2240 de vários contratos, pulando quem já tem evento igual.

        Alterar o laudo de um ambiente afeta todos os trabalhadores dele, e é
        esse o caso de uso real: um evento por trabalhador, com a mesma data de
        início da nova condição.
        """
        criados = self.browse()
        data = fields.Date.to_date(data) or fields.Date.context_today(self)
        for contract in contracts:
            existente = self.search_count(
                [
                    ("contract_id", "=", contract.id),
                    ("dt_ini_condicao", "=", data),
                ]
            )
            if existente:
                continue
            criados |= self.gerar_para_contrato(contract, data=data, laudo=laudo)
        return criados
