# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Parâmetros de ENCARGOS PATRONAIS por empresa (RF-31/RF-32/RF-33).

O custo do empregador não é uma constante: depende de dados cadastrais do
estabelecimento (RAT do CNAE preponderante, FAP, código FPAS e a alíquota de
terceiros correspondente) e do REGIME TRIBUTÁRIO da empresa (regime normal,
Simples Nacional por anexo, opção pela CPRB). Esses parâmetros nascem aqui, no
módulo de folha, porque é a folha que os transforma em rubrica.

Fronteira com o eSocial (importante para não duplicar cadastro): o
``l10n_br_esocial`` deve SERIALIZAR estes campos, não redefini-los.

  - **S-1005** (Tabela de Estabelecimentos), grupo ``aliqGilrat``: declara
    exatamente ``aliqRat``, ``fap`` e ``aliqRatAjust``, que aqui são
    ``l10n_br_hr_rat``, ``l10n_br_hr_fap`` e ``l10n_br_hr_rat_ajustado``.
  - **S-1020** (Tabela de Lotações Tributárias), grupo ``fpasLotacao``: é ali,
    e não no estabelecimento, que moram o código FPAS e o código de terceiros.
    Nesta onda eles ficam na empresa como **lotação padrão**
    (``l10n_br_hr_fpas_padrao`` / ``l10n_br_hr_terceiros_padrao``): quando o
    eSocial trouxer o cadastro de lotações, o campo da empresa passa a ser o
    default da lotação, sem migração de dado.
  - **S-1280** (Informações Complementares aos Eventos Periódicos):
    ``percRedContrib`` é ``l10n_br_hr_cprb_perc_contrib_nao_desonerada``, e o
    ``indSubstPatr`` é DERIVADO dele (0 = 1, substituição integral; > 0 = 2,
    parcial), para que não exista estado contraditório no cadastro.

O regime tributário em si NÃO é redefinido aqui: é o ``tax_framework`` do
``l10n_br_fiscal`` (fonte única na localização, também usada pelo documento
fiscal e pelo custo de estoque), complementado por ``profit_calculation``
(real/presumido). Deste módulo saem apenas os dados que só a folha usa.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from . import salary_rules_br

# Anexos do Simples Nacional (LC 123/2006). O anexo importa para a folha por
# um motivo único: o anexo IV não inclui a CPP no DAS (art. 18, §5º-C).
SIMPLES_ANEXO = [
    ("i", "I - Comércio"),
    ("ii", "II - Indústria"),
    ("iii", "III - Serviços (CPP no DAS)"),
    ("iv", "IV - Serviços com CPP por fora (construção, vigilância, limpeza)"),
    ("v", "V - Serviços (CPP no DAS)"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_br_hr_rat = fields.Selection(
        selection=[
            ("1", "1% - risco leve"),
            ("2", "2% - risco médio"),
            ("3", "3% - risco grave"),
        ],
        string="Alíquota RAT",
        default="1",
        help="Grau de risco de acidente do trabalho do CNAE preponderante do "
        "estabelecimento (Lei 8.212/91, art. 22, II; Anexo V do Decreto "
        "3.048/99). Declarado no eSocial S-1005 (aliqRat).",
    )
    l10n_br_hr_fap = fields.Float(
        string="FAP",
        digits=(5, 4),
        default=1.0,
        help="Fator Acidentário de Prevenção, de 0,5000 a 2,0000, publicado "
        "anualmente pela Previdência por CNPJ (Lei 10.666/2003, art. 10; "
        "Decreto 3.048/99, art. 202-A). Multiplica o RAT. Declarado no "
        "eSocial S-1005 (fap).",
    )
    l10n_br_hr_rat_ajustado = fields.Float(
        string="RAT Ajustado (%)",
        digits=(5, 4),
        compute="_compute_l10n_br_hr_rat_ajustado",
        store=True,
        help="RAT x FAP: alíquota efetivamente devida sobre a remuneração. "
        "Declarada no eSocial S-1005 (aliqRatAjust).",
    )
    l10n_br_hr_fpas_padrao = fields.Char(
        string="Código FPAS Padrão",
        size=3,
        default="507",
        help="Código do Fundo de Previdência e Assistência Social da "
        "atividade (ex.: 507 = indústria), que define o rol de entidades "
        "(terceiros) a que se contribui.\n\n"
        "No eSocial esse enquadramento pertence à LOTAÇÃO TRIBUTÁRIA (S-1020, "
        "grupo fpasLotacao), não ao estabelecimento: uma empresa pode ter "
        "lotações com FPAS diferentes (obra própria, cessão de mão de obra, "
        "etc.). Aqui o campo é a lotação PADRÃO da empresa, usada enquanto o "
        "cadastro de lotações não existir.",
    )
    l10n_br_hr_terceiros_padrao = fields.Float(
        string="Alíquota Terceiros Padrão (%)",
        digits=(5, 2),
        default=5.8,
        help="Alíquota total das contribuições a outras entidades e fundos "
        "(terceiros) do código FPAS da lotação padrão. Indústria (FPAS 507): "
        "5,8% = Salário-Educação 2,5 + INCRA 0,2 + SENAI 1,0 + SESI 1,5 + "
        "SEBRAE 0,6 (Anexo III da IN RFB 2.110/2022). A composição varia por "
        "enquadramento (o SEBRAE em especial), por isso é parâmetro e não "
        "constante do código.",
    )
    l10n_br_hr_prov_ferias_perc_indenizado = fields.Float(
        string="Férias Indenizadas Esperadas (%)",
        digits=(5, 2),
        help="Percentual da provisão de férias que se espera pagar como "
        "verba INDENIZATÓRIA (rescisões, abono). Férias indenizadas e o "
        "respectivo terço não sofrem contribuição previdenciária (Lei "
        "8.212/91, art. 28, §9º, 'd') nem FGTS (Lei 8.036/90, art. 15, §6º), "
        "então essa parcela é excluída da base dos encargos sobre a provisão. "
        "Zero = provisiona encargos sobre a provisão inteira (conservador).",
    )
    l10n_br_hr_simples_anexo = fields.Selection(
        selection=SIMPLES_ANEXO,
        string="Anexo do Simples Nacional",
        help="Anexo preponderante quando a empresa é optante pelo Simples "
        "Nacional. Só o anexo IV recolhe a contribuição patronal por fora do "
        "DAS (LC 123/2006, art. 18, §5º-C); nos anexos I, II, III e V a folha "
        "não gera CPP, RAT nem terceiros (apenas FGTS).",
    )
    l10n_br_hr_cprb_optante = fields.Boolean(
        string="Optante pela CPRB",
        help="Empresa de setor dos arts. 7º/8º da Lei 12.546/2011 que optou "
        "pela contribuição sobre a receita bruta em substituição (parcial, na "
        "transição da Lei 14.973/2024) à contribuição patronal sobre a folha. "
        "A opção é anual e irretratável (art. 9º, §13).",
    )
    l10n_br_hr_cprb_perc_contrib_nao_desonerada = fields.Float(
        string="percRedContrib (%)",
        digits=(5, 2),
        help="Campo percRedContrib do eSocial S-1280: percentual A QUE a "
        "contribuição patronal fica reduzida, igual à proporção da receita "
        "bruta NÃO desonerada sobre a receita bruta total do mês.\n\n"
        "Atenção à direção: desoneração TOTAL informa ZERO (e não 100). É "
        "dado de competência, porque muda a cada mês com o faturamento.\n\n"
        "Quando a receita não desonerada é de até 5% do total, a lei dispensa "
        "a proporcionalização e a CPRB incide sobre a receita inteira "
        "(Lei 12.546/2011, art. 9º, §§5º e 6º): informar zero.",
    )

    @api.depends("l10n_br_hr_rat", "l10n_br_hr_fap")
    def _compute_l10n_br_hr_rat_ajustado(self):
        for company in self:
            company.l10n_br_hr_rat_ajustado = salary_rules_br.aliquota_rat_ajustado(
                float(company.l10n_br_hr_rat or 0), company.l10n_br_hr_fap
            )

    @api.constrains("l10n_br_hr_fap")
    def _check_l10n_br_hr_fap(self):
        """FAP fora de 0,5 a 2,0 é inválido (Decreto 3.048/99, art. 202-A)."""
        for company in self:
            if company.l10n_br_hr_fap and not 0.5 <= company.l10n_br_hr_fap <= 2.0:
                raise ValidationError(
                    _(
                        "O FAP da empresa %(empresa)s deve estar entre 0,5000 e "
                        "2,0000 (Decreto 3.048/99, art. 202-A). Valor informado: "
                        "%(valor)s."
                    )
                    % {
                        "empresa": company.display_name,
                        "valor": company.l10n_br_hr_fap,
                    }
                )

    @api.constrains(
        "l10n_br_hr_cprb_perc_contrib_nao_desonerada",
        "l10n_br_hr_terceiros_padrao",
        "l10n_br_hr_prov_ferias_perc_indenizado",
    )
    def _check_l10n_br_hr_percentuais(self):
        percentuais = {
            "percRedContrib": "l10n_br_hr_cprb_perc_contrib_nao_desonerada",
            "alíquota de terceiros": "l10n_br_hr_terceiros_padrao",
            "percentual de férias indenizadas": (
                "l10n_br_hr_prov_ferias_perc_indenizado"
            ),
        }
        for company in self:
            for label, fname in percentuais.items():
                if not 0.0 <= company[fname] <= 100.0:
                    raise ValidationError(
                        _(
                            "O campo %(campo)s deve estar entre 0 e 100 "
                            "(empresa %(empresa)s)."
                        )
                        % {"campo": label, "empresa": company.display_name}
                    )

    def _l10n_br_hr_cprb_perc_cpp(self, competencia, decimo_terceiro=False):
        """Proporção da CPP sobre a folha na competência, ou ``None``.

        ``None`` significa "não optante pela CPRB" - a CPP é integral e a
        tabela de transição nem é consultada (uma empresa não optante nunca
        deve falhar por falta de vigência da CPRB).
        """
        self.ensure_one()
        if not self.l10n_br_hr_cprb_optante:
            return None
        return self.env["l10n_br.hr.payroll.cprb.transicao"]._proporcao_cpp(
            competencia, decimo_terceiro=decimo_terceiro
        )

    def _l10n_br_hr_aliquotas_patronais(
        self, competencia, simples_anexo=False, aprendiz=False, decimo_terceiro=False
    ):
        """Alíquotas patronais desta empresa na ``competencia``.

        Resolve o regime tributário (``tax_framework``/anexo do Simples), os
        parâmetros do estabelecimento (RAT, FAP, terceiros) e a transição da
        CPRB, e devolve as frações a aplicar sobre a base. A regra de negócio
        propriamente dita fica em ``salary_rules_br.aliquotas_patronais``
        (função pura, testável sem banco).

        Args:
            competencia: Data do fato gerador (competência do holerite).
            simples_anexo: Anexo do Simples da ATIVIDADE do contrato, quando
                diferente do anexo preponderante da empresa (atividade
                concomitante do Simples, eixo independente da CPRB).
            aprendiz: Contrato de aprendizagem (FGTS 2%).
            decimo_terceiro: Apuração do 13º salário. Afeta SOMENTE a CPP: a
                dispensa da Lei 12.546/2011, art. 9º-A, §1º alcança apenas os
                incisos I e III do art. 22 da Lei 8.212/91 - RAT e terceiros
                incidem INTEGRALMENTE sobre a gratificação natalina (zerar o
                bloco patronal inteiro no 13º é o erro clássico).

        Returns:
            Dicionário de frações (ver ``salary_rules_br.aliquotas_patronais``).
        """
        self.ensure_one()
        return salary_rules_br.aliquotas_patronais(
            tax_framework=self.tax_framework,
            simples_anexo=simples_anexo or self.l10n_br_hr_simples_anexo,
            rat=float(self.l10n_br_hr_rat or 0),
            fap=self.l10n_br_hr_fap,
            perc_terceiros=self.l10n_br_hr_terceiros_padrao,
            aprendiz=aprendiz,
            cprb_perc_cpp=self._l10n_br_hr_cprb_perc_cpp(
                competencia, decimo_terceiro=decimo_terceiro
            ),
            cprb_perc_contrib_nao_desonerada=(
                self.l10n_br_hr_cprb_perc_contrib_nao_desonerada
            ),
        )
