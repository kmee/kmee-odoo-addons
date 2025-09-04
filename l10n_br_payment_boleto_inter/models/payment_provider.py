from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("inter", "Banco Inter")],
        ondelete={"inter": "set default"},
    )

    # Configurações específicas do Banco Inter
    inter_conta_corrente = fields.Char(
        string="Conta Corrente",
        help="Número da conta corrente no Banco Inter",
        groups="base.group_system",
    )
    inter_client_id = fields.Char(
        string="Client ID",
        help="Client ID fornecido pelo Banco Inter",
        groups="base.group_system",
    )
    inter_client_secret = fields.Char(
        string="Client Secret",
        help="Client Secret fornecido pelo Banco Inter",
        groups="base.group_system",
    )
    inter_certificate = fields.Binary(
        string="Certificado",
        help="Certificado fornecido pelo Banco Inter (formato PEM)",
        groups="base.group_system",
    )
    inter_private_key = fields.Binary(
        string="Chave Privada",
        help="Chave privada do certificado (formato PEM)",
        groups="base.group_system",
    )

    # @api.constrains("code")
    # def _check_inter_configuration(self):
    #     """Valida configurações obrigatórias para o provider Inter"""
    #     for provider in self:
    #         if provider.code == "inter" and provider.state != "disabled":
    #             required_fields = [
    #                 "inter_conta_corrente",
    #                 "inter_client_id",
    #                 "inter_client_secret",
    #                 "inter_certificate",
    #             ]
    #             missing_fields = []

    #             for field in required_fields:
    #                 if not getattr(provider, field):
    #                     field_label = provider._fields[field].string
    #                     missing_fields.append(field_label)

    #             if missing_fields:
    #                 raise ValidationError(
    #                     _(
    #                         f"Configuração incompleta do Banco Inter. "
    #                         f"Campos obrigatórios: {', '.join(missing_fields)}"
    #                     )
    #                 )

    def _get_supported_currencies(self):
        """Retorna moedas suportadas pelo provider"""
        supported_currencies = super()._get_supported_currencies()
        if self.code == "inter":
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name == "BRL"
            )
        return supported_currencies
