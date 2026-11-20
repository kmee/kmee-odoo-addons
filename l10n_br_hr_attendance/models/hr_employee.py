# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from erpbrasil.base.misc import punctuation_rm

from odoo import api, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def _l10n_br_indice_documentos(self):
        """Índice {documento sem pontuação: funcionário} para conciliação.

        CPF (``vat``, related ao contato de trabalho) e PIS/PASEP têm
        ``groups="hr.group_hr_user"`` no ``l10n_br_hr``; a leitura vai por
        ``sudo`` porque a importação de AFD roda em contexto de integração,
        não de RH.
        """
        indice = {"cpf": {}, "pis": {}}
        for employee in self.sudo().search([]):
            dados = employee.read(["vat", "pis_pasep"])[0]
            cpf = self._l10n_br_normaliza_documento(dados.get("vat"))
            if cpf:
                indice["cpf"].setdefault(cpf, employee)
            pis = self._l10n_br_normaliza_documento(dados.get("pis_pasep"))
            if pis:
                indice["pis"].setdefault(pis, employee)
        return indice

    @api.model
    def _l10n_br_normaliza_documento(self, documento):
        """Tira pontuação e zeros de preenchimento à esquerda.

        Os leiautes reservam 12 posições para documentos de 11 dígitos, então
        o mesmo CPF aparece ora com zero à esquerda, ora sem.
        """
        limpo = punctuation_rm(documento or "").strip()
        if not limpo:
            return ""
        return limpo.lstrip("0").zfill(11)

    @api.model
    def _l10n_br_buscar_por_documento(self, cpf=None, pis=None, indice=None):
        """Concilia por CPF com fallback para PIS/PASEP (RP-07).

        Returns:
            ``hr.employee`` correspondente, ou recordset vazio quando o
            documento não bate com ninguém - caso em que a marcação fica
            pendente em vez de ser descartada.
        """
        indice = indice if indice is not None else self._l10n_br_indice_documentos()
        cpf_limpo = self._l10n_br_normaliza_documento(cpf)
        if cpf_limpo and cpf_limpo in indice["cpf"]:
            return indice["cpf"][cpf_limpo]
        pis_limpo = self._l10n_br_normaliza_documento(pis)
        if pis_limpo and pis_limpo in indice["pis"]:
            return indice["pis"][pis_limpo]
        return self.browse()
