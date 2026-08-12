# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import re

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# Competência mensal (AAAA-MM) e anual (AAAA), conforme TS_perApur do leiaute.
RE_COMPETENCIA_MENSAL = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
RE_COMPETENCIA_ANUAL = re.compile(r"^\d{4}$")
# Recibo de entrega do eSocial: 1.<dígito>.<19 dígitos> (TS_nrRecibo).
RE_NR_RECIBO = re.compile(r"^1\.\d\.\d{19}$")

try:
    from esociallib import to_xml, validate_xsd
except ImportError:
    to_xml = None
    validate_xsd = None
    _logger.warning("esociallib not installed. eSocial XML generation disabled.")


class ESocialBaseIntermediario(models.AbstractModel):
    """Base mixin for eSocial intermediary models.

    Provides common fields and methods for generating events from Odoo records.
    """

    _name = "l10n_br.esocial.base.intermediario"
    _description = "eSocial - Base Intermediário"

    evento_id = fields.Many2one(
        "l10n_br.esocial.evento",
        string="Evento",
        readonly=True,
        ondelete="set null",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    def _get_tp_amb(self):
        """Return environment string for esociallib."""
        tp_amb = self.company_id.l10n_br_esocial_tp_amb or "2"
        return "restricted" if tp_amb == "2" else "production"

    def _get_ide_empregador(self):
        """Return employer identification dict."""
        company = self.company_id
        partner = company.partner_id
        cnpj = partner.cnpj_cpf
        if not cnpj:
            raise UserError(
                _("Empresa '%(company_name)s' não possui CNPJ/CPF configurado.")
                % {"company_name": company.name}
            )
        # Remove punctuation
        cnpj_limpo = "".join(c for c in cnpj if c.isdigit())
        if len(cnpj_limpo) == 14:
            return {"tp_insc": 1, "nr_insc": cnpj_limpo[:8]}
        return {"tp_insc": 2, "nr_insc": cnpj_limpo}

    @api.model
    def _so_digitos(self, valor):
        """Remove pontuação de inscrições e códigos numéricos."""
        return "".join(c for c in (valor or "") if c.isdigit())

    @api.model
    def _validar_competencia(self, valor, rotulo, anual=False):
        """Valida o formato de uma competência do leiaute (AAAA-MM ou AAAA).

        Campo vazio é aceito (a obrigatoriedade é de cada evento). Levanta
        ValidationError para poder ser usado em ``@api.constrains``.
        """
        if not valor:
            return
        if anual:
            valido = RE_COMPETENCIA_ANUAL.match(valor) or RE_COMPETENCIA_MENSAL.match(
                valor
            )
            esperado = "AAAA (anual) ou AAAA-MM (mensal)"
        else:
            valido = RE_COMPETENCIA_MENSAL.match(valor)
            esperado = "AAAA-MM"
        if not valido:
            raise ValidationError(
                _(
                    "%(rotulo)s inválido: %(valor)r. O eSocial espera o formato "
                    "%(esperado)s."
                )
                % {"rotulo": rotulo, "valor": valor, "esperado": esperado}
            )

    @api.model
    def _validar_nr_recibo(self, valor, rotulo):
        """Valida o formato do recibo de entrega (1.d.19 dígitos)."""
        if not valor:
            return
        if not RE_NR_RECIBO.match(valor.strip()):
            raise ValidationError(
                _(
                    "%(rotulo)s inválido: %(valor)r. O recibo de entrega do "
                    "eSocial tem o formato 1.D.<19 dígitos>, por exemplo "
                    "1.2.0000000000000012345."
                )
                % {"rotulo": rotulo, "valor": valor}
            )

    def _get_proc_info(self):
        """Return process emission info."""
        proc_emissao = self.company_id.l10n_br_esocial_processo_emissao or "1"
        return {"proc_emi": int(proc_emissao), "ver_proc": "odoo_16_esocial_1.0"}

    @api.model
    def _check_esociallib(self):
        if to_xml is None:
            raise UserError(
                _(
                    "A biblioteca esociallib não está instalada. "
                    "Execute: pip install esociallib"
                )
            )

    def _to_esociallib_dict(self):
        """Override in subclasses. Must return dict for esociallib builder."""
        raise NotImplementedError

    def _get_event_type(self):
        """Override in subclasses. Must return event type string (e.g. 'S-1010')."""
        raise NotImplementedError

    def _gerar_xml_sem_validacao(self, event_type, data, environment):
        """Fallback generation when the bundled XSD schemas are absent.

        esociallib ships without the official XSDs, so ``to_xml`` raises
        ``FileNotFoundError`` on validation. We still need to emit the event,
        but we refuse to return XML that is not at least well-formed, and we
        log an explicit ERROR so the missing-XSD condition is never silent.
        """
        from esociallib.generator import _BUILDERS, _ensure_builders_loaded

        _ensure_builders_loaded()
        builder = _BUILDERS.get(event_type)
        if builder is None:
            raise UserError(
                _(
                    "Não foi possível gerar o evento %(tipo)s: a esociallib não "
                    "possui um builder registrado para este evento e os schemas "
                    "XSD não estão disponíveis para validação."
                )
                % {"tipo": event_type}
            )
        _logger.error(
            "eSocial %s: schemas XSD ausentes na esociallib — XML gerado SEM "
            "validação XSD. Instale os XSDs oficiais em "
            "esociallib/esocial/schemas/v_s13/ para validar antes de transmitir.",
            event_type,
        )
        evento = builder(data, environment=environment)
        xml = evento.to_xml()
        # Guard: never return XML that is not well-formed.
        try:
            etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        except (etree.XMLSyntaxError, ValueError) as exc:
            raise UserError(
                _(
                    "Falha ao gerar o XML do evento %(tipo)s: o conteúdo gerado "
                    "não é um XML válido (%(erro)s)."
                )
                % {"tipo": event_type, "erro": exc}
            ) from exc
        return xml

    def _gerar_xml(self):
        """Generate XML for this intermediary record."""
        self.ensure_one()
        self._check_esociallib()
        data = self._to_esociallib_dict()
        environment = self._get_tp_amb()
        event_type = self._get_event_type()
        try:
            xml = to_xml(event_type, data, environment=environment)
        except FileNotFoundError:
            xml = self._gerar_xml_sem_validacao(event_type, data, environment)
        return xml

    @api.model
    def _extract_id_evento(self, xml):
        """Extract the eSocial event ``Id`` attribute from generated XML.

        The eSocial layout always wraps the event element as
        ``<eSocial><evtXxx Id="ID...">``, so the Id is the ``Id`` attribute of
        the first child element of the root. Returns ``False`` when it cannot
        be found (never raises, so it never blocks event creation).
        """
        if not xml:
            return False
        try:
            root = etree.fromstring(
                xml.encode("utf-8") if isinstance(xml, str) else xml
            )
        except (etree.XMLSyntaxError, ValueError):
            _logger.warning(
                "eSocial: não foi possível parsear o XML para extrair o Id."
            )
            return False
        for child in root:
            id_evento = child.get("Id")
            if id_evento:
                return id_evento
        return root.get("Id") or False

    def _prepare_evento_vals(self, xml, id_evento):
        """Valores do ``l10n_br.esocial.evento`` gerado por este intermediário.

        Subclasses estendem para carregar competência, retificação ou vínculos
        próprios do evento (ver S-1200, S-1210, S-1299, S-3000).
        """
        self.ensure_one()
        return {
            "tipo": self._get_event_type(),
            "operacao": "I",
            "id_evento": id_evento,
            "xml_envio": xml,
            "company_id": self.company_id.id,
            "origem_model": self._name,
            "origem_id": self.id,
        }

    def action_gerar_evento(self):
        """Generate XML and create evento record."""
        self.ensure_one()
        xml = self._gerar_xml()
        id_evento = self._extract_id_evento(xml)
        if not id_evento:
            _logger.warning(
                "eSocial %s: XML gerado sem atributo Id — o retorno do lote não "
                "poderá casar o evento pelo id_evento.",
                self._get_event_type(),
            )
        evento = self.env["l10n_br.esocial.evento"].create(
            self._prepare_evento_vals(xml, id_evento)
        )
        self.evento_id = evento.id
        return evento
