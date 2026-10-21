# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_br_hr_sst.models.sst_dominios import PERCENTUAL_INSALUBRIDADE

# Ordem de gravidade dos graus de insalubridade da NR-15.
ORDEM_GRAU = {"minimo": 1, "medio": 2, "maximo": 3}

# Periculosidade: 30% do salário-base (CLT, art. 193, par. 1).
PERCENTUAL_PERICULOSIDADE = 30.0

OPCAO_ADICIONAL = [
    ("insalubridade", "Insalubridade"),
    ("periculosidade", "Periculosidade"),
]

# Quem gera o adicional da aposentadoria especial (Lei 10.666/2003, art. 1;
# Decreto 3.048/99, art. 64; IN RFB 2.110/2022, art. 43): empregado (1xx),
# trabalhador avulso (2xx) e cooperado filiado a cooperativa de produção
# (738). Contribuinte individual sem cooperativa não gera RAT nem adicional.
CATEGORIAS_GRUPO_ADICIONAL = ("1", "2")
CATEGORIAS_ADICIONAL = ("738",)

# Código da regra salarial do adicional. Fica aqui para a migração reescrever
# a regra das bases já instaladas (o XML é noupdate) com o mesmo texto.
REGRA_GILRAT_CONDICAO = (
    "result = contract._l10n_br_sst_aliquota_gilrat_em("
    "payslip.date_from, payslip.date_to) > 0"
)
REGRA_GILRAT_VALOR = """aliquota = contract._l10n_br_sst_aliquota_gilrat_em(
    payslip.date_from, payslip.date_to
)
base = categories.GROSS - FALTAS - DESC_DSR
result = tools.br.round_money(max(base, 0) * aliquota / 100.0)"""


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
    l10n_br_sst_opcao_adicional = fields.Selection(
        OPCAO_ADICIONAL,
        string="Opção do Empregado",
        tracking=True,
        help="Quando o laudo aponta insalubridade e periculosidade, os dois "
        "adicionais não se acumulam (CLT, art. 193, par. 2, e TST IRR Tema "
        "17): o empregado opta por um deles. Sem opção registrada, a folha "
        "paga o de maior valor.",
    )
    l10n_br_sst_opcao_data = fields.Date(
        string="Data da Opção",
        tracking=True,
        help="Data em que o empregado manifestou a opção pelo adicional.",
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

    @api.constrains("l10n_br_sst_opcao_adicional", "l10n_br_sst_opcao_data")
    def _check_l10n_br_sst_opcao(self):
        for rec in self:
            if rec.l10n_br_sst_opcao_adicional and not rec.l10n_br_sst_opcao_data:
                raise ValidationError(
                    _(
                        "Contrato %(nome)s: informe a data em que o empregado "
                        "optou pelo adicional."
                    )
                    % {"nome": rec.display_name}
                )

    def _l10n_br_sst_adicional_de_maior_valor(self, grau, data=None):
        """Adicional de maior valor entre insalubridade e periculosidade.

        Insalubridade: percentual do grau sobre o salário mínimo (CLT, art.
        192). Periculosidade: 30% do salário-base. Sem tabela de salário
        mínimo para a data, fica a insalubridade, como antes.
        """
        self.ensure_one()
        data = fields.Date.to_date(data) or fields.Date.context_today(self)
        try:
            minimo = self.env["l10n_br.hr.payroll.inss.faixa"]._salario_minimo(data)
        except UserError:
            return "insalubridade"
        insalubridade = minimo * PERCENTUAL_INSALUBRIDADE.get(grau, 0.0) / 100.0
        periculosidade = (self.wage or 0.0) * PERCENTUAL_PERICULOSIDADE / 100.0
        return "periculosidade" if periculosidade > insalubridade else "insalubridade"

    def _l10n_br_sst_adicionais_esperados(self, data=None):
        """O que a folha deve pagar a partir do laudo, aplicada a vedação.

        Com os dois adicionais no laudo, vale a opção do empregado; sem ela, o
        de maior valor. Nunca os dois (CLT, art. 193, par. 2).
        """
        self.ensure_one()
        esperado = dict(self._l10n_br_sst_adicionais_do_laudo(data))
        if esperado["insalubridade"] and esperado["periculosidade"]:
            escolha = (
                self.l10n_br_sst_opcao_adicional
                or self._l10n_br_sst_adicional_de_maior_valor(esperado["grau"], data)
            )
            if escolha == "periculosidade":
                esperado.update(insalubridade=False, grau=False)
            else:
                esperado["periculosidade"] = False
        return esperado

    def _l10n_br_sst_gera_adicional_gilrat(self):
        """A categoria do trabalhador gera o adicional da aposentadoria especial?

        Sem categoria informada, presume-se empregado: é o caso da folha.
        """
        self.ensure_one()
        codigo = self.employee_id.l10n_br_esocial_categoria_id.codigo or ""
        if not codigo:
            return True
        return codigo[:1] in CATEGORIAS_GRUPO_ADICIONAL or codigo in (
            CATEGORIAS_ADICIONAL
        )

    def _l10n_br_sst_aliquota_gilrat_em(self, inicio, fim=None):
        """Alíquota adicional devida no período, pelos riscos vigentes nele.

        O adicional (12, 9 ou 6 pontos, Tabela 02 do eSocial) entra cheio,
        sem FAP, e só sobre a remuneração de quem esteve exposto no período.
        """
        self.ensure_one()
        inicio = fields.Date.to_date(inicio)
        fim = fields.Date.to_date(fim) or inicio
        if (
            not self.l10n_br_sst_ambiente_id
            or not self._l10n_br_sst_gera_adicional_gilrat()
        ):
            return 0.0
        riscos = self.l10n_br_sst_ambiente_id.risco_ids.filtered(
            lambda r: r.date_from <= fim and (not r.date_to or r.date_to >= inicio)
        )._aplica_a_funcao(self.job_id)
        return riscos._aliquota_gilrat_adicional()

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
        "wage",
        "l10n_br_sst_opcao_adicional",
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
            esperado = rec._l10n_br_sst_adicionais_esperados()
            rec.l10n_br_insalubridade = esperado["insalubridade"]
            rec.l10n_br_grau_insalubridade = esperado["grau"]
            rec.l10n_br_periculosidade = esperado["periculosidade"]

    @api.depends(
        "l10n_br_insalubridade",
        "l10n_br_grau_insalubridade",
        "l10n_br_periculosidade",
        "l10n_br_sst_ambiente_id",
        "job_id",
        "wage",
        "l10n_br_sst_opcao_adicional",
    )
    def _compute_l10n_br_sst_laudo(self):
        """Mostra o laudo e compara o contrato com o que a lei manda pagar.

        A comparação é com o esperado depois da vedação de acúmulo: pagar só
        um dos dois adicionais que o laudo aponta não é divergência.
        """
        for rec in self:
            bruto = rec._l10n_br_sst_adicionais_do_laudo()
            rec.l10n_br_sst_insalubridade_laudo = bruto["insalubridade"]
            rec.l10n_br_sst_grau_laudo = bruto["grau"]
            rec.l10n_br_sst_periculosidade_laudo = bruto["periculosidade"]
            laudo = rec._l10n_br_sst_adicionais_esperados()
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
        "l10n_br_sst_ambiente_id.risco_ids.date_from",
        "l10n_br_sst_ambiente_id.risco_ids.date_to",
        "job_id",
        "employee_id.l10n_br_esocial_categoria_id",
    )
    def _compute_l10n_br_sst_aliquota_gilrat(self):
        """Alíquota de hoje, para a tela; a folha usa a do período."""
        hoje = fields.Date.context_today(self)
        for rec in self:
            rec.l10n_br_sst_aliquota_gilrat = rec._l10n_br_sst_aliquota_gilrat_em(hoje)
