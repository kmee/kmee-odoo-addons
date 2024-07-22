# Copyright (C) 2022-Today - Engenere (<https://engenere.one>).
# @author Antônio S. Pereira Neto <neto@engenere.one>
# Copyright (C) 2024-Today - KMEE (<https://kmee.com.br>).

from odoo import api, fields, models

map_intermediary_type = {
    "conta_propria": "1",
    "conta_ordem": "2",
    "encomenda": "3",
}

map_transportation_type = {
    "maritime": "1",
    "fluvial": "2",
    "lacustrine": "3",
    "aerial": "4",
    "postal": "5",
    "rail": "6",
    "road": "7",
    "conduit": "8",
    "own_means": "9",
    "fict_in_out": "10",
    "courier": "11",
    "in_hands": "12",
    "towing": "13",
}


class FiscalDocumentLine(models.Model):

    _inherit = "l10n_br_fiscal.document.line"

    ##########################
    # NF-e tag: DI
    ##########################

    nfe40_DI = fields.One2many(
        comodel_name="nfe.40.di",
        inverse_name="nfe40_DI_prod_id",
        compute="_compute_nfe40_DI",
        store=True,
    )

    @api.depends("account_line_ids.di_mercadoria_ids", "document_id.state_edoc")
    def _compute_nfe40_DI(self):
        for line in self:
            if not line.document_id._need_compute_nfe_tags:
                continue

            for index, di_mercadoria in enumerate(
                line.account_line_ids.di_mercadoria_ids
            ):
                nfe40_nAdicao_dicts = []

                di = di_mercadoria.declaracao_id
                add = di_mercadoria.adicao_id

                # Prepare the nfe40_nAdicao dicts
                nfe40_nAdicao_dict = {
                    "nfe40_nAdicao": add.numero_adicao,
                    "nfe40_nSeqAdic": index + 1,
                    "nfe40_cFabricante": add.fabricante_partner_id.id,
                    # "nfe40_vDescDI": add.discount_value,
                    # "nfe40_nDraw": add.drawback,
                }
                nfe40_nAdicao_dicts.append((0, 0, nfe40_nAdicao_dict))

                # Prepare the nfe40_DI dict
                nfe40_DI_dict = {
                    "nfe40_DI_prod_id": line.id,
                    "nfe40_nDI": di.numero_di,
                    "nfe40_dDI": di.data_registro,
                    "nfe40_xLocDesemb": di.carga_urf_entrada_nome,
                    # "nfe40_UFDesemb": di.customs_clearance_state_id.code,
                    "nfe40_dDesemb": di.carga_data_chegada,
                    "nfe40_vAFRMM": di_mercadoria.amount_afrmm,
                    # "nfe40_tpViaTransp": map_transportation_type[
                    #     di.transportation_type
                    # ],
                    # "nfe40_tpIntermedio": map_intermediary_type[
                    #     di.intermediary_type
                    # ],
                    # "nfe40_CNPJ": di.third_party_partner_id.cnpj_cpf,
                    # "nfe40_UFTerceiro": di.third_party_partner_id.state_id.code,
                    # "nfe40_cExportador": di.exporting_partner_id.id,
                    "nfe40_adi": nfe40_nAdicao_dicts,  # Link to the nfe40_nAdicao records
                }

                line.nfe40_DI = [(2, d, 0) for d in line.nfe40_DI.ids]
                line.nfe40_DI = [(0, 0, nfe40_DI_dict)]
