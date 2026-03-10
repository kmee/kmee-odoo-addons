import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

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

    def _gerar_xml(self):
        """Generate XML for this intermediary record."""
        self.ensure_one()
        self._check_esociallib()
        data = self._to_esociallib_dict()
        environment = self._get_tp_amb()
        try:
            xml = to_xml(self._get_event_type(), data, environment=environment)
        except FileNotFoundError:
            # XSD schemas not available — generate without validation
            from esociallib.generator import _BUILDERS, _ensure_builders_loaded

            _ensure_builders_loaded()
            builder = _BUILDERS.get(self._get_event_type())
            if builder is None:
                raise
            evento = builder(data, environment=environment)
            xml = evento.to_xml()
            _logger.warning("XSD schemas not found — XML generated without validation")
        return xml

    def action_gerar_evento(self):
        """Generate XML and create evento record."""
        self.ensure_one()
        xml = self._gerar_xml()
        evento = self.env["l10n_br.esocial.evento"].create(
            {
                "tipo": self._get_event_type(),
                "operacao": "I",
                "xml_envio": xml,
                "company_id": self.company_id.id,
                "origem_model": self._name,
                "origem_id": self.id,
            }
        )
        self.evento_id = evento.id
        return evento
