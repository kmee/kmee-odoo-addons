# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# S-1xxx events that belong to the periodic group (grupo 3), not the tables
# group (grupo 1).
PERIODIC_S1_TYPES = frozenset(
    {
        "S-1200",
        "S-1202",
        "S-1207",
        "S-1210",
        "S-1260",
        "S-1270",
        "S-1280",
        "S-1298",
        "S-1299",
    }
)

try:
    from esociallib import assinar, consultar_lote, enviar_lote
except ImportError:
    assinar = None
    consultar_lote = None
    enviar_lote = None
    _logger.warning("esociallib not installed. eSocial transmission disabled.")


class ESocialLote(models.Model):
    _name = "l10n_br.esocial.lote"
    _description = "eSocial - Lote de Transmissão"
    _order = "create_date desc"

    name = fields.Char(compute="_compute_name", store=True)
    state = fields.Selection(
        [
            ("draft", "Rascunho"),
            ("sent", "Enviado"),
            ("processing", "Processando"),
            ("done", "Concluído"),
            ("error", "Erro"),
        ],
        default="draft",
        index=True,
    )
    evento_ids = fields.One2many(
        "l10n_br.esocial.evento",
        "lote_id",
        string="Eventos",
    )
    evento_count = fields.Integer(
        compute="_compute_evento_count",
    )
    protocolo = fields.Char(
        help="Protocolo de envio retornado pelo governo.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.depends("protocolo", "create_date")
    def _compute_name(self):
        for rec in self:
            if rec.protocolo:
                rec.name = f"Lote {rec.protocolo}"
            elif rec.create_date:
                rec.name = f"Lote {rec.create_date.strftime('%Y-%m-%d %H:%M')}"
            else:
                rec.name = "Lote Novo"

    @api.depends("evento_ids")
    def _compute_evento_count(self):
        for rec in self:
            rec.evento_count = len(rec.evento_ids)

    def action_add_validated_events(self):
        """Add all validated events without a lote to this lote."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("Só é possível adicionar eventos a lotes em rascunho.")
                )
            events = self.env["l10n_br.esocial.evento"].search(
                [
                    ("state", "=", "validated"),
                    ("lote_id", "=", False),
                    ("company_id", "=", rec.company_id.id),
                ]
            )
            events.write({"lote_id": rec.id})

    def action_reset_draft(self):
        for rec in self:
            if rec.state not in ("sent", "error"):
                raise UserError(
                    _("Apenas lotes enviados ou com erro podem voltar a rascunho.")
                )
            rec.state = "draft"

    def _get_certificate(self):
        """Get A1 certificate from l10n_br_fiscal_certificate if available."""
        company = self.company_id
        if hasattr(company, "_get_br_ecertificate"):
            cert = company._get_br_ecertificate()
            if cert:
                pfx_data = base64.b64decode(cert.file)
                senha = cert.password
                return pfx_data, senha
        raise UserError(
            _(
                "Certificado digital A1 não configurado para a empresa "
                "'%(company_name)s'. Instale o módulo l10n_br_fiscal_certificate "
                "e configure o certificado."
            )
            % {"company_name": company.name}
        )

    def action_transmitir(self):
        """Sign events and submit batch to eSocial."""
        self.ensure_one()
        if assinar is None or enviar_lote is None:
            raise UserError(
                _("esociallib não está instalada. Execute: pip install esociallib")
            )
        if self.state != "draft":
            raise UserError(_("Apenas lotes em rascunho podem ser transmitidos."))
        if not self.evento_ids:
            raise UserError(_("O lote não possui eventos."))

        eventos_validados = self.evento_ids.filtered(lambda e: e.state == "validated")
        if not eventos_validados:
            raise UserError(
                _("Nenhum evento validado no lote. Valide os eventos primeiro.")
            )
        if len(eventos_validados) > 50:
            raise UserError(
                _("Máximo 50 eventos por lote (%(count)s encontrados).")
                % {"count": len(eventos_validados)}
            )

        pfx_data, senha = self._get_certificate()
        tp_amb = self.company_id.l10n_br_esocial_tp_amb or "2"
        environment = "restricted" if tp_amb == "2" else "production"

        # Determine grupo and enforce lote homogeneity: a single lote must
        # only carry events of the same eSocial group.
        grupo = self._get_lote_grupo(eventos_validados)

        # Sign and transmit inside a single guarded block: any failure must
        # roll back (via UserError) so we never persist signed XML with the
        # lote left in an inconsistent state.
        try:
            eventos_xml = []
            for evento in eventos_validados:
                if not evento.xml_envio:
                    raise UserError(
                        _("Evento %(name)s não possui XML de envio.")
                        % {"name": evento.name}
                    )
                xml_assinado = assinar(evento.xml_envio, pfx_data, senha)
                evento.xml_envio = xml_assinado
                eventos_xml.append(xml_assinado)

            protocolo = enviar_lote(
                eventos_xml,
                pfx_data,
                senha,
                environment=environment,
                grupo=grupo,
            )
        except UserError:
            raise
        except Exception as exc:
            _logger.exception("Erro ao assinar/transmitir lote eSocial %s", self.id)
            raise UserError(
                _("Falha na assinatura/transmissão do lote: %(erro)s") % {"erro": exc}
            ) from exc

        self.protocolo = protocolo
        self.state = "sent"
        eventos_validados.write({"state": "sent"})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Lote Transmitido"),
                "message": _("Protocolo: %(protocolo)s") % {"protocolo": protocolo},
                "type": "success",
            },
        }

    @api.model
    def _classify_grupo(self, tipo):
        """Return the eSocial transmission group (1/2/3) for an event type.

        1 = Tabelas, 2 = Não-periódicos (S-2xxx / S-3xxx), 3 = Periódicos.
        """
        tipo = tipo or ""
        if tipo.startswith("S-1") and tipo not in PERIODIC_S1_TYPES:
            return 1
        if tipo.startswith("S-2") or tipo.startswith("S-3"):
            return 2
        return 3

    def _get_lote_grupo(self, eventos):
        """Validate group homogeneity and return the single group of the lote."""
        self.ensure_one()
        grupos = {self._classify_grupo(tipo) for tipo in eventos.mapped("tipo")}
        if len(grupos) > 1:
            labels = {1: "1-Tabelas", 2: "2-Não Periódicos", 3: "3-Periódicos"}
            raise UserError(
                _(
                    "O lote contém eventos de grupos eSocial diferentes (%(grupos)s). "
                    "Cada lote deve conter apenas eventos de um mesmo grupo. "
                    "Separe os eventos em lotes distintos."
                )
                % {"grupos": ", ".join(labels[g] for g in sorted(grupos))}
            )
        return grupos.pop()

    def action_consultar(self):
        """Query batch result from eSocial."""
        self.ensure_one()
        if consultar_lote is None:
            raise UserError(_("esociallib não está instalada."))
        if not self.protocolo:
            raise UserError(_("Lote sem protocolo. Transmita primeiro."))

        pfx_data, senha = self._get_certificate()
        tp_amb = self.company_id.l10n_br_esocial_tp_amb or "2"
        environment = "restricted" if tp_amb == "2" else "production"

        resultado = consultar_lote(
            self.protocolo,
            pfx_data,
            senha,
            environment=environment,
        )

        if resultado.status == "processado":
            self.state = "done"
            for evt_result in resultado.eventos:
                # Match event by id_evento
                event_id = evt_result.event_id
                evento = self.evento_ids.filtered(
                    lambda e, eid=event_id: e.id_evento and e.id_evento == eid
                )
                if not evento:
                    _logger.warning(
                        "eSocial lote %s: retorno com event_id %s não casou com "
                        "nenhum evento do lote.",
                        self.id,
                        evt_result.event_id,
                    )
                    continue
                retorno_xml = getattr(evt_result, "retorno_xml", None)
                if evt_result.aceito:
                    # registrar_aceite concentra recibo, XML de retorno,
                    # totalizadores devolvidos e propagação do S-3000.
                    evento.registrar_aceite(
                        nr_recibo=evt_result.nr_recibo,
                        retorno_xml=retorno_xml,
                    )
                else:
                    if retorno_xml:
                        evento.xml_retorno = retorno_xml
                    evento.write({"state": "error"})
                    self.env["l10n_br.esocial.ocorrencia"].create(
                        {
                            "evento_id": evento.id,
                            "codigo": evt_result.code or "",
                            "descricao": evt_result.description or "",
                            "tipo": "1",
                        }
                    )
            # If any event has error, mark lote as error
            if self.evento_ids.filtered(lambda e: e.state == "error"):
                self.state = "error"
        elif resultado.status == "em_processamento":
            self.state = "processing"
        else:
            self.state = "error"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Consulta Lote"),
                "message": _("Status: %(status)s") % {"status": resultado.status},
                "type": "info" if resultado.status != "erro" else "danger",
            },
        }
