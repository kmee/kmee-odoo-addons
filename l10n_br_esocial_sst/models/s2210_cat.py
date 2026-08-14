# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ESocialS2210(models.Model):
    """S-2210 - Comunicação de Acidente de Trabalho.

    Desde 2023 este evento É a CAT: o CATWeb foi descontinuado. O prazo é o do
    art. 22 da Lei 8.213/91, primeiro dia útil seguinte ao acidente e imediato
    no óbito, e ele é acompanhado no próprio registro da CAT.
    """

    _name = "l10n_br.esocial.s2210"
    _inherit = "l10n_br.esocial.base.sst"
    _description = "eSocial S-2210 - Comunicação de Acidente de Trabalho"
    _order = "id desc"

    name = fields.Char(compute="_compute_name", store=True)
    cat_id = fields.Many2one(
        "l10n_br.sst.cat",
        string="CAT",
        required=True,
        ondelete="cascade",
    )
    acidente_id = fields.Many2one(
        related="cat_id.acidente_id",
        store=True,
        readonly=True,
    )

    @api.depends("cat_id")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.cat_id.name

    def _get_event_type(self):
        return "S-2210"

    def _validar_antes_do_envio(self):
        for rec in self:
            acidente = rec.acidente_id
            faltando = []
            if not acidente.situacao_geradora_id:
                faltando.append(_("situação geradora"))
            if not acidente.parte_corpo_id:
                faltando.append(_("parte do corpo atingida"))
            if not acidente.agente_causador_id:
                faltando.append(_("agente causador"))
            if not acidente.dsc_lograd or not acidente.nr_lograd:
                faltando.append(_("logradouro e número do local do acidente"))
            if not acidente.date_atendimento:
                faltando.append(_("data do atendimento"))
            if not acidente.hora_atendimento:
                faltando.append(_("hora do atendimento"))
            if not acidente.dur_trat:
                faltando.append(_("duração do tratamento"))
            if not acidente.natureza_lesao_id:
                faltando.append(_("natureza da lesão"))
            if not acidente.cid_id:
                faltando.append(_("CID"))
            if not acidente.nm_emit:
                faltando.append(_("emitente do atestado"))
            if not acidente.ide_oc_emit or not acidente.nr_oc_emit:
                faltando.append(_("órgão de classe e número do emitente"))
            if faltando:
                raise UserError(
                    _(
                        "S-2210 de %(nome)s: informe %(campos)s antes de "
                        "transmitir a CAT."
                    )
                    % {
                        "nome": rec.employee_id.name,
                        "campos": ", ".join(faltando),
                    }
                )
            if acidente.houve_obito and not acidente.date_obito:
                raise UserError(
                    _("S-2210 de %(nome)s: informe a data do óbito.")
                    % {"nome": rec.employee_id.name}
                )
            if rec.cat_id.tipo_cat_codigo in ("2", "3") and not (
                rec.cat_id.nr_rec_cat_orig
            ):
                raise UserError(
                    _(
                        "S-2210 de %(nome)s: a CAT de reabertura ou de óbito "
                        "exige o recibo da comunicação anterior."
                    )
                    % {"nome": rec.employee_id.name}
                )

    def action_gerar_evento(self):
        self._validar_antes_do_envio()
        return super().action_gerar_evento()

    # Mapeamentos opcionais: (campo do acidente, chave da esociallib). Um
    # dicionário de tradução evita a escada de ifs que o leiaute induz.
    _CAMPOS_OPCIONAIS_CAT = (
        ("hora_acidente", "hr_acid"),
        ("hrs_trab_antes_acid", "hrs_trab_antes_acid"),
        ("observacao", "obs_cat"),
    )
    _CAMPOS_OPCIONAIS_LOCAL = (
        ("dsc_local", "dsc_local"),
        ("dsc_lograd", "dsc_lograd"),
        ("nr_lograd", "nr_lograd"),
        ("complemento_local", "complemento_local"),
        ("bairro_local", "bairro_local"),
    )
    _CAMPOS_OPCIONAIS_ATESTADO = (
        ("hora_atendimento", "hr_atendimento"),
        ("dsc_comp_lesao", "dsc_comp_lesao"),
        ("diagnostico_provavel", "diag_provavel"),
        ("observacao_atestado", "observacao_atestado"),
        ("nr_oc_emit", "nr_oc"),
    )

    @api.model
    def _copiar_opcionais(self, dados, origem, campos):
        for campo, chave in campos:
            valor = origem[campo]
            if valor:
                dados[chave] = valor

    def _to_cat(self, dados):
        """Grupo cat: o acidente em si."""
        acidente = self.acidente_id
        dados.update(
            {
                "dt_acid": str(acidente.date_acidente),
                "tp_acid": int(acidente.tp_acid),
                "tp_cat": int(self.cat_id.tipo_cat_codigo),
                "ind_cat_obito": "S" if acidente.houve_obito else "N",
                "ind_comun_policia": "S" if acidente.comunicacao_policia else "N",
                "cod_sit_geradora": acidente.situacao_geradora_id.codigo,
                "iniciat_cat": int(acidente.iniciat_cat),
            }
        )
        self._copiar_opcionais(dados, acidente, self._CAMPOS_OPCIONAIS_CAT)
        if acidente.houve_obito:
            dados["dt_obito"] = str(acidente.date_obito)
        if acidente.ultimo_dia_trabalhado:
            dados["ult_dia_trab"] = str(acidente.ultimo_dia_trabalhado)
        if acidente.houve_afastamento:
            dados["houve_afast"] = "S"

    def _to_local_acidente(self, dados):
        """Grupos localAcidente e ideLocalAcid."""
        acidente = self.acidente_id
        dados["tp_local"] = int(acidente.tp_local)
        self._copiar_opcionais(dados, acidente, self._CAMPOS_OPCIONAIS_LOCAL)
        if acidente.cep_local:
            dados["cep_local"] = self._so_digitos(acidente.cep_local)
        if acidente.city_id:
            dados["cod_munic_local"] = self._so_digitos(
                acidente.city_id.ibge_code or ""
            )
        if acidente.state_id:
            dados["uf_local"] = acidente.state_id.code
        if acidente.tp_insc_local and acidente.nr_insc_local:
            dados["tp_insc_local"] = int(acidente.tp_insc_local)
            dados["nr_insc_local"] = self._so_digitos(acidente.nr_insc_local)

    def _to_lesao_e_atestado(self, dados):
        """Grupos parteAtingida, agenteCausador, atestado e emitente."""
        acidente = self.acidente_id
        dados.update(
            {
                "cod_parte_ating": acidente.parte_corpo_id.codigo,
                "lateralidade": int(acidente.lateralidade or "0"),
                "cod_agnt_causador": acidente.agente_causador_id.codigo,
                "dt_atendimento": str(acidente.date_atendimento),
                "ind_internacao": acidente.ind_internacao or "N",
                "ind_afast": acidente.ind_afast or "N",
                "dsc_lesao": acidente.natureza_lesao_id.codigo,
                "nm_emit": acidente.nm_emit,
            }
        )
        self._copiar_opcionais(dados, acidente, self._CAMPOS_OPCIONAIS_ATESTADO)
        if acidente.dur_trat:
            dados["dur_trat"] = str(acidente.dur_trat)
        if acidente.cid_id:
            dados["cod_cid"] = acidente.cid_id.codigo
        if acidente.ide_oc_emit:
            dados["ide_oc"] = int(acidente.ide_oc_emit)
        if acidente.uf_oc_emit:
            dados["uf_oc"] = acidente.uf_oc_emit.upper()

    def _to_esociallib_dict(self):
        self.ensure_one()
        self._validar_antes_do_envio()
        dados = self._get_dados_comuns()
        self._to_cat(dados)
        self._to_local_acidente(dados)
        self._to_lesao_e_atestado(dados)
        if self.cat_id.nr_rec_cat_orig:
            dados["nr_rec_cat_orig"] = self.cat_id.nr_rec_cat_orig
        return dados
