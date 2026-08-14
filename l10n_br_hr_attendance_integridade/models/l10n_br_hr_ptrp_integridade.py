# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, models
from odoo.modules.module import get_module_path

from . import ptrp_escopo

_logger = logging.getLogger(__name__)

PARAM_RESUMO_HOMOLOGADO = "l10n_br_hr_attendance_aej.ptrp_resumo_homologado"
PARAM_VERSAO_ATESTADA = "l10n_br_hr_attendance_aej.ptrp_versao_atestada"


class L10nBrHrPtrpIntegridade(models.AbstractModel):
    """Verificação de integridade do PTRP.

    Duas camadas, porque uma sozinha não responde a pergunta:

    - **fonte**: o código do escopo atestado é o mesmo que foi homologado?
    - **execução**: algum módulo instalado sobrepõe os modelos do PTRP ou
      injeta código sobre eles? No Odoo dá para alterar o resultado sem tocar
      em nenhum arquivo deste repositório, então conferir só os arquivos daria
      uma resposta tranquilizadora e errada.
    """

    _name = "l10n_br.hr.ptrp.integridade"
    _description = "Integridade do PTRP"

    # ------------------------------------------------------------------
    # Camada 1: código-fonte do escopo atestado
    # ------------------------------------------------------------------

    @api.model
    def _manifesto_fonte(self):
        """Manifesto do escopo atestado, apenas dos módulos instalados."""
        instalados = set(
            self.env["ir.module.module"]
            .sudo()
            .search([("state", "=", "installed")])
            .mapped("name")
        )
        entradas = []
        for modulo, padroes in sorted(ptrp_escopo.NUCLEO_ATESTADO.items()):
            if modulo not in instalados:
                continue
            caminho = get_module_path(modulo, display_warning=False)
            if not caminho:
                continue
            entradas.extend(ptrp_escopo.manifesto_do_modulo(caminho, modulo, padroes))
        return entradas

    @api.model
    def resumo_fonte(self):
        """Resumo digital do escopo atestado em execução neste servidor."""
        return ptrp_escopo.resumo_do_manifesto(self._manifesto_fonte())

    # ------------------------------------------------------------------
    # Camada 2: sobreposições em tempo de execução
    # ------------------------------------------------------------------

    @api.model
    def _extensoes_de_terceiros(self):
        """Módulos fora do PTRP que definem ou estendem os modelos atestados."""
        achados = []
        modelos = (
            self.env["ir.model"]
            .sudo()
            .search([("model", "in", list(ptrp_escopo.MODELOS_ATESTADOS))])
        )
        for modelo in modelos:
            terceiros = [
                nome.strip()
                for nome in (modelo.modules or "").split(",")
                if nome.strip() and nome.strip() not in ptrp_escopo.MODULOS_DO_PTRP
            ]
            for modulo in terceiros:
                achados.append(
                    _("Modelo %(modelo)s estendido pelo módulo %(modulo)s.")
                    % {"modelo": modelo.model, "modulo": modulo}
                )
        return achados

    @api.model
    def _codigo_em_banco(self):
        """Código Python guardado no banco que atua sobre os modelos do PTRP.

        Ação de servidor e automação executam código arbitrário e não deixam
        rastro em arquivo nenhum: é o caminho mais curto para alterar o
        resultado de uma apuração sem alterar o programa.
        """
        achados = []
        acoes = (
            self.env["ir.actions.server"]
            .sudo()
            .search(
                [
                    ("state", "=", "code"),
                    ("model_id.model", "in", list(ptrp_escopo.MODELOS_ATESTADOS)),
                ]
            )
        )
        for acao in acoes:
            achados.append(
                _("Ação de servidor com código sobre %(modelo)s: %(nome)s.")
                % {"modelo": acao.model_id.model, "nome": acao.name}
            )
        if "base.automation" in self.env:
            automacoes = (
                self.env["base.automation"]
                .sudo()
                .search([("model_id.model", "in", list(ptrp_escopo.MODELOS_ATESTADOS))])
            )
            for automacao in automacoes:
                achados.append(
                    _("Automação sobre %(modelo)s: %(nome)s.")
                    % {"modelo": automacao.model_id.model, "nome": automacao.name}
                )
        return achados

    # ------------------------------------------------------------------
    # Diagnóstico consolidado
    # ------------------------------------------------------------------

    @api.model
    def verificar(self):
        """Estado da integridade do PTRP neste servidor.

        Returns:
            Dicionário com ``resumo``, ``homologado``, ``versao``,
            ``confere`` (``None`` quando não há resumo homologado
            configurado), ``divergencias`` e ``manifesto``.
        """
        parametro = self.env["ir.config_parameter"].sudo()
        homologado = (parametro.get_param(PARAM_RESUMO_HOMOLOGADO) or "").strip()
        manifesto = self._manifesto_fonte()
        resumo = ptrp_escopo.resumo_do_manifesto(manifesto)
        divergencias = self._extensoes_de_terceiros() + self._codigo_em_banco()
        return {
            "resumo": resumo,
            "homologado": homologado,
            "versao": parametro.get_param(PARAM_VERSAO_ATESTADA) or "",
            "confere": (resumo == homologado) if homologado else None,
            "divergencias": divergencias,
            "manifesto": manifesto,
        }

    @api.model
    def texto_do_diagnostico(self):
        """Diagnóstico em texto, para chatter, log e anexo do arquivo."""
        estado = self.verificar()
        linhas = [
            _("Resumo do escopo atestado: %s") % estado["resumo"],
        ]
        if estado["versao"]:
            linhas.append(_("Versão atestada: %s") % estado["versao"])
        if estado["confere"] is None:
            linhas.append(
                _(
                    "Não há resumo homologado configurado: a conferência "
                    "contra o Atestado Técnico não pôde ser feita."
                )
            )
        elif estado["confere"]:
            linhas.append(_("Escopo atestado confere com o homologado."))
        else:
            linhas.append(
                _(
                    "ATENÇÃO: o escopo atestado DIVERGE do homologado "
                    "(esperado %s). O Atestado Técnico não cobre esta versão."
                )
                % estado["homologado"]
            )
        if estado["divergencias"]:
            linhas.append(_("Extensões encontradas sobre o PTRP:"))
            linhas.extend("- " + item for item in estado["divergencias"])
        return "\n".join(linhas)

    @api.model
    def imprimir_manifesto(self):
        """Manifesto em texto canônico, para anexar ao Atestado Técnico.

        É este arquivo que permite a um terceiro recalcular o resumo e provar
        exatamente quais linhas do escopo mudaram entre duas versões.
        """
        estado = self.verificar()
        linhas = [
            "%s:%s" % (caminho, resumo)
            for caminho, resumo in sorted(estado["manifesto"])
        ]
        linhas.append("")
        linhas.append("resumo=%s" % estado["resumo"])
        return "\n".join(linhas)
