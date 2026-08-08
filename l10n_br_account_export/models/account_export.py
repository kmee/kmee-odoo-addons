# Copyright 2026 KMEE INFORMATICA LTDA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from io import StringIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class AccountExport(models.Model):
    """Lote de exportacao de lancamentos para o sistema do escritorio contabil.

    E um modelo persistente, nao um assistente: os parametros usados ficam
    gravados no registro, o que preserva o historico do que foi enviado e
    quando. O vinculo com os lancamentos e feito por um campo no proprio
    ``account.move``, entao desfazer a exportacao e simplesmente apagar o lote.
    """

    _name = "l10n_br.account.export"
    _description = "Exportacao Contabil"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _check_company_auto = True

    name = fields.Char(default="/", copy=False, readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
        states={"draft": [("readonly", False)]},
    )
    config_id = fields.Many2one(
        "l10n_br.account.export.config",
        string="Configuracao",
        required=True,
        check_company=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    layout = fields.Selection(
        related="config_id.layout",
        store=True,
        string="Layout de destino",
    )
    date_start = fields.Date(
        string="De",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date_end = fields.Date(
        string="Ate",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    journal_ids = fields.Many2many(
        "account.journal",
        string="Diarios",
        check_company=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Vazio exporta todos os diarios da empresa.",
    )
    target_move = fields.Selection(
        [("posted", "Somente lancados"), ("all", "Todos")],
        default="posted",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    move_ids = fields.One2many(
        "account.move",
        "l10n_br_account_export_id",
        string="Lancamentos",
        readonly=True,
    )
    move_count = fields.Integer(compute="_compute_counts", store=True)
    line_count = fields.Integer(compute="_compute_counts", store=True)
    state = fields.Selection(
        [("draft", "Rascunho"), ("done", "Gerado")],
        default="draft",
        required=True,
        readonly=True,
        tracking=True,
    )
    attachment_id = fields.Many2one(
        "ir.attachment", string="Arquivo", readonly=True, copy=False
    )
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        domain=[("res_model", "=", "l10n_br.account.export")],
        string="Arquivos gerados",
        readonly=True,
        help="Alguns layouts entregam mais de um arquivo (lancamentos, plano de "
        "contas, terceiros).",
    )
    partial_export = fields.Boolean(
        string="Exportar validos e listar rejeitados",
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="Sem esta opcao nenhum arquivo e gerado enquanto houver critica. "
        "Com ela, os lancamentos criticados saem do lote.",
    )
    critica = fields.Text(string="Criticas", readonly=True, copy=False)

    @api.depends("move_ids")
    def _compute_counts(self):
        for export in self:
            export.move_count = len(export.move_ids)
            export.line_count = len(export._get_export_lines())

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "l10n_br.account.export"
                ) or _("Exportacao")
        return super().create(vals_list)

    def unlink(self):
        if any(export.state == "done" for export in self):
            raise UserError(
                _(
                    "Volte o lote para rascunho antes de apagar, para liberar os "
                    "lancamentos vinculados."
                )
            )
        return super().unlink()

    # ------------------------------------------------------------------
    # selecao de lancamentos
    # ------------------------------------------------------------------
    def _prepare_move_domain(self):
        """Lancamentos do periodo que ainda nao foram exportados.

        O filtro por ``l10n_br_account_export_id = False`` e o que garante que um
        lancamento nao seja enviado duas vezes ao contador.
        """
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("l10n_br_account_export_id", "=", False),
            ("date", ">=", self.date_start),
            ("date", "<=", self.date_end),
        ]
        if self.journal_ids:
            domain.append(("journal_id", "in", self.journal_ids.ids))
        if self.target_move == "posted":
            domain.append(("state", "=", "posted"))
        else:
            domain.append(("state", "in", ("draft", "posted")))
        return domain

    def action_get_moves(self):
        """Traz para o lote os lancamentos do periodo."""
        for export in self:
            if export.state != "draft":
                raise UserError(_("So e possivel buscar lancamentos em rascunho."))
            export.move_ids.write({"l10n_br_account_export_id": False})
            moves = self.env["account.move"].search(export._prepare_move_domain())
            if not moves:
                raise UserError(
                    _(
                        "Nenhum lancamento encontrado para o periodo e os filtros "
                        "informados."
                    )
                )
            moves.write({"l10n_br_account_export_id": export.id})
        return True

    def _get_export_lines(self, move=None):
        """Partidas exportaveis, sem as linhas de secao e de anotacao."""
        moves = move if move is not None else self.move_ids
        return moves.line_ids.filtered(
            lambda x: x.display_type not in ("line_section", "line_note")
        )

    # ------------------------------------------------------------------
    # validacao
    # ------------------------------------------------------------------
    def _validate_export(self):
        """Criticas que impedem um arquivo correto.

        O balanco debito/credito e verificado por seguranca, mas na pratica o
        Odoo ja o garante ao lancar. A critica que de fato pega erro em campo e a
        conta sem codigo no plano do escritorio.
        """
        self.ensure_one()
        criticas = []
        rounding = self.company_id.currency_id.rounding

        sem_codigo = self.env["account.account"]
        for line in self._get_export_lines():
            if not line.account_id.l10n_br_export_code:
                sem_codigo |= line.account_id
        for conta in sem_codigo:
            qtd = len(
                self._get_export_lines().filtered(lambda x, c=conta: x.account_id == c)
            )
            criticas.append(
                _(
                    "Conta %(code)s (%(name)s) sem codigo no sistema do escritorio: "
                    "%(qtd)s partida(s)."
                )
                % {"code": conta.code, "name": conta.name, "qtd": qtd}
            )

        for move in self.move_ids:
            lines = self._get_export_lines(move)
            saldo = sum(lines.mapped("debit")) - sum(lines.mapped("credit"))
            if not float_is_zero(saldo, precision_rounding=rounding):
                criticas.append(
                    _("Lancamento %(name)s desbalanceado (diferenca de %(saldo)s).")
                    % {"name": move.name, "saldo": saldo}
                )
        return criticas

    def _drop_invalid_moves(self):
        """Solta do lote os lancamentos que nao podem ser exportados."""
        self.ensure_one()
        invalid = self.env["account.move"]
        for move in self.move_ids:
            if any(
                not line.account_id.l10n_br_export_code
                for line in self._get_export_lines(move)
            ):
                invalid |= move
        if invalid:
            invalid.write({"l10n_br_account_export_id": False})
        return invalid

    # ------------------------------------------------------------------
    # geracao
    # ------------------------------------------------------------------
    def _layout_method(self, prefix="_generate"):
        """Nome do metodo que implementa o layout escolhido.

        Cada adapter registra seu valor no Selection ``layout`` e implementa
        ``_generate_<layout>``; nao ha registro central para manter, e o modulo
        de layouts pode ser instalado ou removido sem tocar neste.
        """
        self.ensure_one()
        return f"{prefix}_{self.layout}"

    def _generate_files(self):
        """Devolve [(nome do arquivo, bytes)] do layout escolhido."""
        self.ensure_one()
        method = self._layout_method()
        if not hasattr(self, method):
            raise UserError(
                _(
                    "O layout %s nao esta implementado nesta base. Instale o modulo "
                    "de layouts correspondente."
                )
                % (self.layout or "-")
            )
        return getattr(self, method)()

    def action_generate(self):
        for export in self:
            if export.state != "draft":
                raise UserError(_("Este lote ja foi gerado."))
            if not export.move_ids:
                export.action_get_moves()

            criticas = export._validate_export()
            export.critica = "\n".join(criticas) if criticas else False
            if criticas and not export.partial_export:
                raise UserError(
                    _(
                        "A exportacao tem %(qtd)s critica(s) e nenhum arquivo foi "
                        "gerado:\n\n%(lista)s\n\nCorrija os apontamentos ou marque "
                        "'Exportar validos e listar rejeitados'."
                    )
                    % {"qtd": len(criticas), "lista": "\n".join(criticas)}
                )
            if criticas:
                export._drop_invalid_moves()
                if not export.move_ids:
                    raise UserError(_("Nao sobrou lancamento valido para exportar."))

            arquivos = export._generate_files()
            if not arquivos:
                raise UserError(_("O layout nao produziu nenhum arquivo."))

            export.attachment_ids.unlink()
            anexos = self.env["ir.attachment"]
            for nome, conteudo in arquivos:
                anexos |= self.env["ir.attachment"].create(
                    {
                        "name": nome,
                        "raw": conteudo,
                        "res_model": "l10n_br.account.export",
                        "res_id": export.id,
                    }
                )
            export.write({"state": "done", "attachment_id": anexos[:1].id})
            export._warn_previous_exports()
        return True

    def action_back_to_draft(self):
        for export in self:
            export.attachment_ids.unlink()
            export.move_ids.write({"l10n_br_account_export_id": False})
            export.write({"state": "draft", "attachment_id": False})
        return True

    def _previous_exports(self):
        """Lotes ja gerados com periodo sobreposto, no mesmo layout."""
        self.ensure_one()
        return self.search(
            [
                ("id", "!=", self.id),
                ("company_id", "=", self.company_id.id),
                ("config_id", "=", self.config_id.id),
                ("state", "=", "done"),
                ("date_start", "<=", self.date_end),
                ("date_end", ">=", self.date_start),
            ]
        )

    def _warn_previous_exports(self):
        """Avisa sobre remessa anterior do mesmo periodo, sem bloquear.

        Reexportar e legitimo: lancamentos entram depois do primeiro envio. O
        que evita duplicidade e o vinculo do lancamento com o lote.
        """
        self.ensure_one()
        anteriores = self._previous_exports()
        if anteriores:
            self.message_post(
                body=_(
                    "Este periodo ja teve exportacao gerada (%(lotes)s). Confirme "
                    "com o escritorio para nao duplicar lancamentos no destino."
                )
                % {"lotes": ", ".join(anteriores.mapped("name"))}
            )

    # ------------------------------------------------------------------
    # utilidades para os adapters
    # ------------------------------------------------------------------
    def _file_name(self, sufixo="", extensao="txt"):
        """Nome de arquivo estavel: mesma entrada gera o mesmo nome."""
        self.ensure_one()
        periodo = self.date_start and self.date_start.strftime("%Y%m") or ""
        partes = [self.layout or "export", periodo]
        if sufixo:
            partes.append(sufixo)
        return "_".join(p for p in partes if p) + "." + extensao

    def _encode(self, text):
        """Codifica no charset do destino (ANSI na maioria dos sistemas)."""
        self.ensure_one()
        encoding = self.config_id.encoding or "cp1252"
        return text.encode(encoding, errors="replace")

    def _new_buffer(self):
        return StringIO()

    # ------------------------------------------------------------------
    # utilidades compartilhadas pelos adapters de layout
    # ------------------------------------------------------------------
    def _split_sides(self, move):
        """Separa as partidas em lado devedor e lado credor."""
        lines = self._get_export_lines(move)
        return lines.filtered(lambda x: x.debit), lines.filtered(lambda x: x.credit)

    def _pair_entries(self, move, rateio=""):
        """Devolve (conta_debito, conta_credito, valor, historico, data).

        Boa parte dos layouts espera debito e credito na MESMA linha. Num
        lancamento simples sai um unico par com as duas contas. Em partidas
        multiplas nao existe par: cada linha detalha o seu lado e o outro recebe
        o codigo de rateio do layout (o Dominio usa "0", outros deixam vazio).
        """
        debitos, creditos = self._split_sides(move)
        if not debitos or not creditos:
            return []

        def conta(line):
            return line.account_id.l10n_br_export_code or ""

        def hist(line):
            return line.name or move.ref or ""

        if len(debitos) == 1 and len(creditos) == 1:
            return [
                (
                    conta(debitos),
                    conta(creditos),
                    debitos.debit,
                    hist(debitos) or hist(creditos),
                    move.date,
                )
            ]
        res = []
        for line in debitos:
            res.append((conta(line), rateio, line.debit, hist(line), move.date))
        for line in creditos:
            res.append((rateio, conta(line), line.credit, hist(line), move.date))
        return res
