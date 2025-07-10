# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FiscalDocumentLineMixin(models.AbstractModel):

    _inherit = "l10n_br_fiscal.document.line.mixin"

    issqn_base_manual = fields.Monetary(
        string="Manual ISSQN Base",
        help="Value of the ISSQN Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    issqn_value_manual = fields.Monetary(
        string="Manual ISSQN Value",
        help="Value of the ISSQN Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    issqn_wh_base_manual = fields.Monetary(
        string="Manual ISSQN RET Base",
        help="Value of the ISSQN RET Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    issqn_wh_value_manual = fields.Monetary(
        string="Manual ISSQN RET Value",
        help="Value of the ISSQN RET Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    icms_base_manual = fields.Monetary(
        string="Manual ICMS Base",
        help="Value of the ICMS Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    icms_value_manual = fields.Monetary(
        string="Manual ICMS Value",
        help="Value of the ICMS Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    icmsst_base_manual = fields.Monetary(
        string="Manual ICMS ST Base",
        help="Value of the ICMS ST Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    icmsst_value_manual = fields.Monetary(
        string="Manual ICMS ST Value",
        help="Value of the ICMS ST Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    icmsst_wh_base_manual = fields.Monetary(
        string="Manual ICMS ST RET Base",
        help="Value of the ICMS ST RET Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    icmsst_wh_value_manual = fields.Monetary(
        string="Manual ICMS ST RET Value",
        help="Value of the ICMS ST RET Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    ipi_base_manual = fields.Monetary(
        string="Manual IPI Base",
        help="Value of the IPI Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    ipi_value_manual = fields.Monetary(
        string="Manual IPI Value",
        help="Value of the IPI Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    ii_base_manual = fields.Monetary(
        string="Manual II Base",
        help="Value of the II Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    ii_value_manual = fields.Monetary(
        string="Manual II Value",
        help="Value of the II Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    cofins_base_manual = fields.Monetary(
        string="Manual COFINS Base",
        help="Value of the COFINS Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    cofins_value_manual = fields.Monetary(
        string="Manual COFINS Value",
        help="Value of the COFINS Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    cofinsst_base_manual = fields.Monetary(
        string="Manual COFINS ST Base",
        help="Value of the COFINS ST Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    cofinsst_value_manual = fields.Monetary(
        string="Manual COFINS ST Value",
        help="Value of the COFINS ST Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    cofins_wh_base_manual = fields.Monetary(
        string="Manual COFINS RET Base",
        help="Value of the COFINS RET Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    cofins_wh_value_manual = fields.Monetary(
        string="Manual COFINS RET Value",
        help="Value of the COFINS RET Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    pis_base_manual = fields.Monetary(
        string="Manual PIS Base",
        help="Value of the PIS Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    pis_value_manual = fields.Monetary(
        string="Manual PIS Value",
        help="Value of the PIS Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    pisst_base_manual = fields.Monetary(
        string="Manual PIS ST Base",
        help="Value of the PIS ST Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    pisst_value_manual = fields.Monetary(
        string="Manual PIS ST Value",
        help="Value of the PIS ST Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    pis_wh_base_manual = fields.Monetary(
        string="Manual PIS RET Base",
        help="Value of the PIS RET Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    pis_wh_value_manual = fields.Monetary(
        string="Manual PIS RET Value",
        help="Value of the PIS RET Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    csll_base_manual = fields.Monetary(
        string="Manual CSLL Base",
        help="Value of the CSLL Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    csll_value_manual = fields.Monetary(
        string="Manual CSLL Value",
        help="Value of the CSLL Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    csll_wh_base_manual = fields.Monetary(
        string="Manual CSLL RET Base",
        help="Value of the CSLL RET Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    csll_wh_value_manual = fields.Monetary(
        string="Manual CSLL RET Value",
        help="Value of the CSLL RET Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    irpj_base_manual = fields.Monetary(
        string="Manual IRPJ Base",
        help="Value of the IRPJ Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    irpj_value_manual = fields.Monetary(
        string="Manual IRPJ Value",
        help="Value of the IRPJ Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    irpj_wh_base_manual = fields.Monetary(
        string="Manual IRPJ RET Base",
        help="Value of the IRPJ RET Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    irpj_wh_value_manual = fields.Monetary(
        string="Manual IRPJ RET Value",
        help="Value of the IRPJ RET Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    inss_base_manual = fields.Monetary(
        string="Manual INSS Base",
        help="Value of the INSS Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    inss_value_manual = fields.Monetary(
        string="Manual INSS Value",
        help="Value of the INSS Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
    inss_wh_base_manual = fields.Monetary(
        string="Manual INSS RET Base",
        help="Value of the INSS RET Base calculated manually. "
        "Leave this field blank for automatic calculation.",
    )

    inss_wh_value_manual = fields.Monetary(
        string="Manual INSS Value",
        help="Value of the INSS Value calculated manually. "
        "Leave this field blank for automatic calculation.",
    )
