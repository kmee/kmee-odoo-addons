# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ESocialBaseSst(models.AbstractModel):
    """Parte comum dos eventos de SST ligados a um trabalhador.

    Os quatro eventos de SST usam o mesmo grupo ``ideVinculo`` (CPF, matrícula
    e, na falta dela, categoria), e todos precisam do CPF sem pontuação. Reunir
    isso aqui evita repetir a mesma armadilha em quatro lugares.
    """

    _name = "l10n_br.esocial.base.sst"
    _inherit = "l10n_br.esocial.base.intermediario"
    _description = "eSocial - Base dos Eventos de SST"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Trabalhador",
        required=True,
        ondelete="cascade",
    )
    ind_retif = fields.Selection(
        [
            ("1", "1 - Arquivo original"),
            ("2", "2 - Arquivo de retificação"),
        ],
        string="Indicativo de Retificação",
        default="1",
        required=True,
    )
    nr_recibo = fields.Char(
        string="Recibo do Evento Retificado",
        help="Obrigatório na retificação.",
    )

    def _get_cpf_trabalhador(self):
        self.ensure_one()
        cpf = self.employee_id.cnpj_cpf
        if not cpf:
            raise UserError(
                _("Trabalhador '%(name)s' não possui CPF configurado.")
                % {"name": self.employee_id.name}
            )
        return self._so_digitos(cpf)

    def _get_ide_vinculo(self):
        """Grupo ideVinculo dos eventos de SST."""
        self.ensure_one()
        dados = {"cpf_trab": self._get_cpf_trabalhador()}
        matricula = self.employee_id.l10n_br_esocial_matricula
        if matricula:
            dados["matricula"] = matricula
        else:
            categoria = self.employee_id.l10n_br_esocial_categoria_id
            if categoria:
                dados["cod_categ"] = categoria.codigo
        return dados

    def _get_dados_comuns(self):
        """ideEmpregador, ideEvento e ideVinculo, na forma da esociallib."""
        self.ensure_one()
        ide = self._get_ide_empregador()
        proc = self._get_proc_info()
        dados = {
            "tp_insc": ide["tp_insc"],
            "nr_insc": ide["nr_insc"],
            "proc_emi": proc["proc_emi"],
            "ver_proc": proc["ver_proc"],
            "ind_retif": int(self.ind_retif),
        }
        if self.ind_retif == "2":
            if not self.nr_recibo:
                raise UserError(
                    _(
                        "Retificação do evento %(tipo)s exige o número do "
                        "recibo do evento retificado."
                    )
                    % {"tipo": self._get_event_type()}
                )
            dados["nr_recibo"] = self.nr_recibo
        dados.update(self._get_ide_vinculo())
        return dados
