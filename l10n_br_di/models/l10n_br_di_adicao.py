# flake8: noqa: B950
# Copyright 2024 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from .l10n_br_di_declaracao import D2


class L10nBrDiAdicao(models.Model):

    _name = "l10n_br_di.adicao"
    _inherit = "l10n_br_di.mixin"
    _description = "Declaração Importação Adição"

    _rec_name = "numero_adicao"

    @api.depends("di_adicao_valor_ids")
    def _compute_totals(self):
        for record in self:
            adicao = sum(x.valor for x in record.di_adicao_valor_ids)
            if adicao < 0:
                record.amount_add_ded_brl = adicao
            else:
                record.amount_add_ded_brl = (
                    adicao
                    + record.valor_reais_frete_internacional
                    + record.valor_reais_seguro_internacional
                )

    declaracao_id = fields.Many2one(
        "l10n_br_di.declaracao", string="Declaração", required=True, ondelete="cascade"
    )

    di_adicao_mercadoria_ids = fields.One2many("l10n_br_di.mercadoria", "adicao_id")
    di_adicao_valor_ids = fields.One2many("l10n_br_di.valor", "adicao_id")

    cide_valor_aliquota_especifica = fields.Monetary(currency_field="currency_id")
    cide_valor_devido = fields.Monetary(currency_field="currency_id")
    cide_valor_recolher = fields.Monetary(currency_field="currency_id")
    codigo_relacao_comprador_vendedor = fields.Char()
    codigo_vinculo_comprador_vendedor = fields.Char()
    cofins_aliquota_ad_valorem = fields.Monetary(currency_field="currency_id")
    cofins_aliquota_especifica_quantidade_unidade = fields.Float()
    cofins_aliquota_especifica_valor = fields.Monetary(currency_field="currency_id")
    cofins_aliquota_reduzida = fields.Char()
    cofins_aliquota_valor_devido = fields.Monetary(currency_field="currency_id")
    cofins_aliquota_valor_recolher = fields.Monetary(currency_field="currency_id")
    condicao_venda_incoterm = fields.Char()
    condicao_venda_local = fields.Char()
    condicao_venda_metodo_valoracao_codigo = fields.Char()
    condicao_venda_metodo_valoracao_nome = fields.Char()
    condicao_venda_moeda_codigo = fields.Char()
    condicao_venda_moeda_nome = fields.Char()
    condicao_venda_valor_moeda = fields.Monetary(
        currency_field="moeda_venda_id",
    )
    condicao_venda_valor_reais = fields.Monetary(
        currency_field="currency_id",
    )
    dados_cambiais_cobertura_cambial_codigo = fields.Char()
    dados_cambiais_cobertura_cambial_nome = fields.Char()
    dados_cambiais_instituicao_financiadora_codigo = fields.Char()
    dados_cambiais_instituicao_financiadora_nome = fields.Char()
    dados_cambiais_motivo_sem_cobertura_codigo = fields.Char()
    dados_cambiais_motivo_sem_cobertura_nome = fields.Char()
    dados_cambiais_valor_real_cambio = fields.Monetary(currency_field="currency_id")
    dados_carga_pais_procedencia_codigo = fields.Char()
    dados_carga_urf_entrada_codigo = fields.Char()
    dados_carga_via_transporte_codigo = fields.Char()
    dados_mercadoria_aplicacao = fields.Char()
    dados_mercadoria_codigo_naladi_ncca = fields.Char()
    dados_mercadoria_codigo_naladi_sh = fields.Char()
    dados_mercadoria_codigo_ncm = fields.Char()
    dados_mercadoria_condicao = fields.Char()
    dados_mercadoria_medida_estatistica_quantidade = fields.Float()
    dados_mercadoria_medida_estatistica_unidade = fields.Char()
    dados_mercadoria_nome_ncm = fields.Char()
    dados_mercadoria_peso_liquido = fields.Char()
    dcr_coeficiente_reducao = fields.Char()
    dcr_identificacao = fields.Char()
    dcr_valor_devido = fields.Monetary(currency_field="currency_id")
    dcr_valor_dolar = fields.Monetary(currency_field="dolar_currency_id")
    dcr_valor_real = fields.Monetary(currency_field="currency_id")
    dcr_valor_recolher = fields.Monetary(currency_field="currency_id")

    fabricante_partner_id = fields.Many2one("res.partner")

    fabricante_cidade = fields.Char()
    fabricante_estado = fields.Char()
    fabricante_logradouro = fields.Char()
    fabricante_nome = fields.Char()
    fabricante_numero = fields.Char()
    fornecedor_cidade = fields.Char()
    fornecedor_complemento = fields.Char()
    fornecedor_estado = fields.Char()
    fornecedor_logradouro = fields.Char()
    fornecedor_nome = fields.Char()
    fornecedor_numero = fields.Char()

    fornecedor_partner_id = fields.Many2one("res.partner")

    frete_moeda_negociada_codigo = fields.Monetary(currency_field="currency_id")
    frete_valor_moeda_negociada = fields.Monetary(currency_field="moeda_frete_id")
    frete_valor_reais = fields.Monetary(currency_field="currency_id")
    ii_acordo_tarifario_aladi_codigo = fields.Char()
    ii_acordo_tarifario_aladi_nome = fields.Char()
    ii_acordo_tarifario_ato_legal_ano = fields.Char()
    ii_acordo_tarifario_ato_legal_codigo = fields.Char()
    ii_acordo_tarifario_ato_legal_ex = fields.Char()
    ii_acordo_tarifario_ato_legal_numero = fields.Char()
    ii_acordo_tarifario_ato_legal_orgao_emissor = fields.Char()
    ii_acordo_tarifario_tipo_codigo = fields.Char()
    ii_acordo_tarifario_tipo_nome = fields.Char()
    ii_aliquota_acordo = fields.Char()
    ii_aliquota_ad_valorem = fields.Monetary(currency_field="currency_id")
    ii_aliquota_percentual_reducao = fields.Float()
    ii_aliquota_reduzida = fields.Char()
    ii_aliquota_valor_calculado = fields.Monetary(currency_field="currency_id")
    ii_aliquota_valor_devido = fields.Monetary(currency_field="currency_id")
    ii_aliquota_valor_recolher = fields.Monetary(currency_field="currency_id")
    ii_aliquota_valor_reduzido = fields.Monetary(currency_field="currency_id")
    ii_base_calculo = fields.Char()
    ii_fundamento_legal_codigo = fields.Char()
    ii_motivo_admissao_temporaria_codigo = fields.Char()
    ii_regime_tributacao_codigo = fields.Char()
    ii_regime_tributacao_nome = fields.Char()
    ipi_aliquota_ad_valorem = fields.Monetary(currency_field="currency_id")
    ipi_aliquota_especifica_capacidade_recipciente = fields.Char()
    ipi_aliquota_especifica_quantidade_unidade_medida = fields.Float()
    ipi_aliquota_especifica_tipo_recipiente_codigo = fields.Char()
    ipi_aliquota_especifica_valor_unidade_medida = fields.Monetary(
        currency_field="currency_id"
    )
    ipi_aliquota_nota_complementar_tipi = fields.Char()
    ipi_aliquota_reduzida = fields.Char()
    ipi_aliquota_valor_devido = fields.Monetary(currency_field="currency_id")
    ipi_aliquota_valor_recolher = fields.Monetary(currency_field="currency_id")
    ipi_regime_tributacao_codigo = fields.Char()
    ipi_regime_tributacao_nome = fields.Char()
    numero_adicao = fields.Char()
    numero_di = fields.Char()
    numero_li = fields.Char()
    pais_aquisicao_mercadoria_codigo = fields.Char()
    pais_aquisicao_mercadoria_nome = fields.Char()
    pais_origem_mercadoria_codigo = fields.Char()
    pais_origem_mercadoria_nome = fields.Char()
    pis_cofins_base_calculo_aliquota_icms = fields.Char()
    pis_cofins_base_calculo_fundamento_legal_codigo = fields.Char()
    pis_cofins_base_calculo_percentual_reducao = fields.Float()
    pis_cofins_base_calculo_valor = fields.Monetary(currency_field="currency_id")
    pis_cofins_fundamento_legal_reducao_codigo = fields.Char()
    pis_cofins_regime_tributacao_codigo = fields.Char()
    pis_cofins_regime_tributacao_nome = fields.Char()
    pis_pasep_aliquota_ad_valorem = fields.Monetary(currency_field="currency_id")
    pis_pasep_aliquota_especifica_quantidade_unidade = fields.Float()
    pis_pasep_aliquota_especifica_valor = fields.Monetary(currency_field="currency_id")
    pis_pasep_aliquota_reduzida = fields.Char()
    pis_pasep_aliquota_valor_devido = fields.Monetary(currency_field="currency_id")
    pis_pasep_aliquota_valor_recolher = fields.Monetary(currency_field="currency_id")
    relacao_comprador_vendedor = fields.Char()
    seguro_moeda_negociada_codigo = fields.Char()
    seguro_valor_moeda_negociada = fields.Monetary(currency_field="moeda_seguro_id")
    seguro_valor_reais = fields.Monetary(currency_field="currency_id")
    sequencial_retificacao = fields.Char()
    valor_multa_arecolher = fields.Monetary(currency_field="currency_id")
    valor_multa_arecolher_ajustado = fields.Monetary(currency_field="currency_id")
    valor_reais_frete_internacional = fields.Monetary(currency_field="currency_id")
    valor_reais_seguro_internacional = fields.Monetary(currency_field="currency_id")
    valor_total_condicao_venda = fields.Monetary(currency_field="currency_id")
    vinculo_comprador_vendedor = fields.Char()

    currency_id = fields.Many2one("res.currency", related="declaracao_id.currency_id")
    dolar_currency_id = fields.Many2one(
        "res.currency", related="declaracao_id.dolar_currency_id"
    )
    moeda_venda_id = fields.Many2one("res.currency")
    moeda_seguro_id = fields.Many2one("res.currency")
    moeda_frete_id = fields.Many2one("res.currency")

    taxa_cambio_venda = fields.Float()
    taxa_cambio_frete = fields.Float()
    taxa_cambio_seguro = fields.Float()

    amount_add_ded_brl = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_totals",
    )

    valor_taxa_siscomex = fields.Monetary(currency_field="currency_id")
    valor_taxa_capatazia = fields.Monetary(currency_field="currency_id")
    valor_taxa_afrmm = fields.Monetary(currency_field="currency_id")
    valor_outros = fields.Monetary(currency_field="currency_id")

    def _importa_declaracao(self, adicao):
        mercadorias = []
        valores = []

        for despacho in adicao.mercadoria:
            mercadorias.append(
                self.di_adicao_mercadoria_ids._importa_declaracao(despacho)
            )
        if adicao.deducao or adicao.acrescimo:
            valores = self.di_adicao_valor_ids._importa_declaracao(
                adicao.acrescimo, adicao.deducao
            )

        moeda_venda_id = self._s_currency(adicao.condicao_venda_moeda_codigo)
        moeda_seguro_id = self._s_currency(adicao.seguro_moeda_negociada_codigo)
        moeda_frete_id = self._s_currency(adicao.frete_moeda_negociada_codigo)

        condicao_venda_valor_reais = int(adicao.condicao_venda_valor_reais) / D2
        condicao_venda_valor_moeda = int(adicao.condicao_venda_valor_moeda) / D2

        if condicao_venda_valor_reais and condicao_venda_valor_moeda:
            taxa_cambio_venda = condicao_venda_valor_reais / condicao_venda_valor_moeda
        else:
            taxa_cambio_venda = 1

        frete_valor_moeda_negociada = int(adicao.frete_valor_moeda_negociada) / D2
        frete_valor_reais = int(adicao.frete_valor_reais) / D2

        if frete_valor_reais and frete_valor_moeda_negociada:
            taxa_cambio_frete = frete_valor_reais / frete_valor_moeda_negociada
        else:
            taxa_cambio_frete = 1

        seguro_valor_moeda_negociada = int(adicao.seguro_valor_moeda_negociada) / D2
        seguro_valor_reais = int(adicao.seguro_valor_reais) / D2

        if seguro_valor_reais and seguro_valor_moeda_negociada:
            taxa_cambio_seguro = seguro_valor_reais / seguro_valor_moeda_negociada
        else:
            taxa_cambio_seguro = 1

        vals = {
            "moeda_venda_id": moeda_venda_id.id if moeda_venda_id else False,
            "moeda_seguro_id": moeda_seguro_id.id if moeda_seguro_id else False,
            "moeda_frete_id": moeda_frete_id.id if moeda_frete_id else False,
            "taxa_cambio_venda": taxa_cambio_venda,
            "taxa_cambio_seguro": taxa_cambio_seguro,
            "taxa_cambio_frete": taxa_cambio_frete,
            "di_adicao_mercadoria_ids": [(0, 0, x) for x in mercadorias],
            "di_adicao_valor_ids": [(0, 0, x) for x in valores],
            "valor_total_condicao_venda": int(adicao.valor_total_condicao_venda) / D2,
            "cide_valor_aliquota_especifica": adicao.cide_valor_aliquota_especifica,
            "cide_valor_devido": adicao.cide_valor_devido,
            "cide_valor_recolher": adicao.cide_valor_recolher,
            "codigo_relacao_comprador_vendedor": adicao.codigo_relacao_comprador_vendedor,
            "codigo_vinculo_comprador_vendedor": adicao.codigo_vinculo_comprador_vendedor,
            "cofins_aliquota_ad_valorem": adicao.cofins_aliquota_ad_valorem,
            "cofins_aliquota_especifica_quantidade_unidade": adicao.cofins_aliquota_especifica_quantidade_unidade,
            "cofins_aliquota_especifica_valor": adicao.cofins_aliquota_especifica_valor,
            "cofins_aliquota_reduzida": adicao.cofins_aliquota_reduzida,
            "cofins_aliquota_valor_devido": adicao.cofins_aliquota_valor_devido,
            "cofins_aliquota_valor_recolher": adicao.cofins_aliquota_valor_recolher,
            "condicao_venda_incoterm": adicao.condicao_venda_incoterm,
            "condicao_venda_local": adicao.condicao_venda_local,
            "condicao_venda_metodo_valoracao_codigo": adicao.condicao_venda_metodo_valoracao_codigo,
            "condicao_venda_metodo_valoracao_nome": adicao.condicao_venda_metodo_valoracao_nome,
            "condicao_venda_moeda_codigo": adicao.condicao_venda_moeda_codigo,
            "condicao_venda_moeda_nome": adicao.condicao_venda_moeda_nome,
            "condicao_venda_valor_moeda": condicao_venda_valor_moeda,
            "condicao_venda_valor_reais": condicao_venda_valor_reais,
            "dados_cambiais_cobertura_cambial_codigo": adicao.dados_cambiais_cobertura_cambial_codigo,
            "dados_cambiais_cobertura_cambial_nome": adicao.dados_cambiais_cobertura_cambial_nome,
            "dados_cambiais_instituicao_financiadora_codigo": adicao.dados_cambiais_instituicao_financiadora_codigo,
            "dados_cambiais_instituicao_financiadora_nome": adicao.dados_cambiais_instituicao_financiadora_nome,
            "dados_cambiais_motivo_sem_cobertura_codigo": adicao.dados_cambiais_motivo_sem_cobertura_codigo,
            "dados_cambiais_motivo_sem_cobertura_nome": adicao.dados_cambiais_motivo_sem_cobertura_nome,
            "dados_cambiais_valor_real_cambio": adicao.dados_cambiais_valor_real_cambio,
            "dados_carga_pais_procedencia_codigo": adicao.dados_carga_pais_procedencia_codigo,
            "dados_carga_urf_entrada_codigo": adicao.dados_carga_urf_entrada_codigo,
            "dados_carga_via_transporte_codigo": adicao.dados_carga_via_transporte_codigo,
            "dados_mercadoria_aplicacao": adicao.dados_mercadoria_aplicacao,
            "dados_mercadoria_codigo_naladi_ncca": adicao.dados_mercadoria_codigo_naladi_ncca,
            "dados_mercadoria_codigo_naladi_sh": adicao.dados_mercadoria_codigo_naladi_sh,
            "dados_mercadoria_codigo_ncm": adicao.dados_mercadoria_codigo_ncm,
            "dados_mercadoria_condicao": adicao.dados_mercadoria_condicao,
            "dados_mercadoria_medida_estatistica_quantidade": adicao.dados_mercadoria_medida_estatistica_quantidade,
            "dados_mercadoria_medida_estatistica_unidade": adicao.dados_mercadoria_medida_estatistica_unidade,
            "dados_mercadoria_nome_ncm": adicao.dados_mercadoria_nome_ncm,
            "dados_mercadoria_peso_liquido": adicao.dados_mercadoria_peso_liquido,
            "dcr_coeficiente_reducao": adicao.dcr_coeficiente_reducao,
            "dcr_identificacao": adicao.dcr_identificacao,
            "dcr_valor_devido": adicao.dcr_valor_devido,
            "dcr_valor_dolar": adicao.dcr_valor_dolar,
            "dcr_valor_real": adicao.dcr_valor_real,
            "dcr_valor_recolher": adicao.dcr_valor_recolher,
            "fabricante_cidade": adicao.fabricante_cidade,
            "fabricante_estado": adicao.fabricante_estado,
            "fabricante_logradouro": adicao.fabricante_logradouro,
            "fabricante_nome": adicao.fabricante_nome,
            "fabricante_numero": adicao.fabricante_numero,
            "fornecedor_cidade": adicao.fornecedor_cidade,
            "fornecedor_complemento": adicao.fornecedor_complemento,
            "fornecedor_estado": adicao.fornecedor_estado,
            "fornecedor_logradouro": adicao.fornecedor_logradouro,
            "fornecedor_nome": adicao.fornecedor_nome,
            "fornecedor_numero": adicao.fornecedor_numero,
            "frete_moeda_negociada_codigo": adicao.frete_moeda_negociada_codigo,
            "frete_valor_moeda_negociada": frete_valor_moeda_negociada,
            "frete_valor_reais": frete_valor_reais,
            "ii_acordo_tarifario_aladi_codigo": adicao.ii_acordo_tarifario_aladi_codigo,
            "ii_acordo_tarifario_aladi_nome": adicao.ii_acordo_tarifario_aladi_nome,
            "ii_acordo_tarifario_ato_legal_ano": adicao.ii_acordo_tarifario_ato_legal_ano,
            "ii_acordo_tarifario_ato_legal_codigo": adicao.ii_acordo_tarifario_ato_legal_codigo,
            "ii_acordo_tarifario_ato_legal_ex": adicao.ii_acordo_tarifario_ato_legal_ex,
            "ii_acordo_tarifario_ato_legal_numero": adicao.ii_acordo_tarifario_ato_legal_numero,
            "ii_acordo_tarifario_ato_legal_orgao_emissor": adicao.ii_acordo_tarifario_ato_legal_orgao_emissor,
            "ii_acordo_tarifario_tipo_codigo": adicao.ii_acordo_tarifario_tipo_codigo,
            "ii_acordo_tarifario_tipo_nome": adicao.ii_acordo_tarifario_tipo_nome,
            "ii_aliquota_acordo": adicao.ii_aliquota_acordo,
            "ii_aliquota_ad_valorem": adicao.ii_aliquota_ad_valorem,
            "ii_aliquota_percentual_reducao": adicao.ii_aliquota_percentual_reducao,
            "ii_aliquota_reduzida": adicao.ii_aliquota_reduzida,
            "ii_aliquota_valor_calculado": adicao.ii_aliquota_valor_calculado,
            "ii_aliquota_valor_devido": adicao.ii_aliquota_valor_devido,
            "ii_aliquota_valor_recolher": adicao.ii_aliquota_valor_recolher,
            "ii_aliquota_valor_reduzido": adicao.ii_aliquota_valor_reduzido,
            "ii_base_calculo": adicao.ii_base_calculo,
            "ii_fundamento_legal_codigo": adicao.ii_fundamento_legal_codigo,
            "ii_motivo_admissao_temporaria_codigo": adicao.ii_motivo_admissao_temporaria_codigo,
            "ii_regime_tributacao_codigo": adicao.ii_regime_tributacao_codigo,
            "ii_regime_tributacao_nome": adicao.ii_regime_tributacao_nome,
            "ipi_aliquota_ad_valorem": adicao.ipi_aliquota_ad_valorem,
            "ipi_aliquota_especifica_capacidade_recipciente": adicao.ipi_aliquota_especifica_capacidade_recipciente,
            "ipi_aliquota_especifica_quantidade_unidade_medida": adicao.ipi_aliquota_especifica_quantidade_unidade_medida,
            "ipi_aliquota_especifica_tipo_recipiente_codigo": adicao.ipi_aliquota_especifica_tipo_recipiente_codigo,
            "ipi_aliquota_especifica_valor_unidade_medida": adicao.ipi_aliquota_especifica_valor_unidade_medida,
            "ipi_aliquota_nota_complementar_tipi": adicao.ipi_aliquota_nota_complementar_tipi,
            "ipi_aliquota_reduzida": adicao.ipi_aliquota_reduzida,
            "ipi_aliquota_valor_devido": adicao.ipi_aliquota_valor_devido,
            "ipi_aliquota_valor_recolher": adicao.ipi_aliquota_valor_recolher,
            "ipi_regime_tributacao_codigo": adicao.ipi_regime_tributacao_codigo,
            "ipi_regime_tributacao_nome": adicao.ipi_regime_tributacao_nome,
            "numero_adicao": adicao.numero_adicao,
            "numero_di": adicao.numero_di,
            "numero_li": adicao.numero_li,
            "pais_aquisicao_mercadoria_codigo": adicao.pais_aquisicao_mercadoria_codigo,
            "pais_aquisicao_mercadoria_nome": adicao.pais_aquisicao_mercadoria_nome,
            "pais_origem_mercadoria_codigo": adicao.pais_origem_mercadoria_codigo,
            "pais_origem_mercadoria_nome": adicao.pais_origem_mercadoria_nome,
            "pis_cofins_base_calculo_aliquota_icms": adicao.pis_cofins_base_calculo_aliquota_icms,
            "pis_cofins_base_calculo_fundamento_legal_codigo": adicao.pis_cofins_base_calculo_fundamento_legal_codigo,
            "pis_cofins_base_calculo_percentual_reducao": adicao.pis_cofins_base_calculo_percentual_reducao,
            "pis_cofins_base_calculo_valor": adicao.pis_cofins_base_calculo_valor,
            "pis_cofins_fundamento_legal_reducao_codigo": adicao.pis_cofins_fundamento_legal_reducao_codigo,
            "pis_cofins_regime_tributacao_codigo": adicao.pis_cofins_regime_tributacao_codigo,
            "pis_cofins_regime_tributacao_nome": adicao.pis_cofins_regime_tributacao_nome,
            "pis_pasep_aliquota_ad_valorem": adicao.pis_pasep_aliquota_ad_valorem,
            "pis_pasep_aliquota_especifica_quantidade_unidade": adicao.pis_pasep_aliquota_especifica_quantidade_unidade,
            "pis_pasep_aliquota_especifica_valor": adicao.pis_pasep_aliquota_especifica_valor,
            "pis_pasep_aliquota_reduzida": adicao.pis_pasep_aliquota_reduzida,
            "pis_pasep_aliquota_valor_devido": adicao.pis_pasep_aliquota_valor_devido,
            "pis_pasep_aliquota_valor_recolher": adicao.pis_pasep_aliquota_valor_recolher,
            "relacao_comprador_vendedor": adicao.relacao_comprador_vendedor,
            "seguro_moeda_negociada_codigo": adicao.seguro_moeda_negociada_codigo,
            "seguro_valor_moeda_negociada": seguro_valor_moeda_negociada,
            "seguro_valor_reais": seguro_valor_reais,
            "sequencial_retificacao": adicao.sequencial_retificacao,
            "valor_multa_arecolher": adicao.valor_multa_arecolher,
            "valor_multa_arecolher_ajustado": adicao.valor_multa_arecolher_ajustado,
            "valor_reais_frete_internacional": int(
                adicao.valor_reais_frete_internacional
            )
            / D2,
            "valor_reais_seguro_internacional": int(
                adicao.valor_reais_seguro_internacional
            )
            / D2,
            "vinculo_comprador_vendedor": adicao.vinculo_comprador_vendedor,
        }

        if adicao.fabricante_nome:

            manufacturer_id = self.env["res.partner"].search(
                [("name", "=", adicao.fabricante_nome)]
            )
            if not manufacturer_id:
                manufacturer_id = self.env["res.partner"].create(
                    {
                        "name": adicao.fabricante_nome,
                        "legal_name": adicao.fabricante_nome,
                        "street_number": adicao.fabricante_numero,
                        "street": adicao.fabricante_logradouro,
                        "city": adicao.fabricante_cidade,
                    }
                )
            vals.update(
                {
                    "fabricante_partner_id": manufacturer_id.id,
                }
            )

        fornecedor_partner_id = self.env["res.partner"].search(
            [("name", "=", adicao.fornecedor_nome)]
        )
        if not fornecedor_partner_id:
            fornecedor_partner_id = self.env["res.partner"].create(
                {
                    "name": adicao.fornecedor_nome,
                    "legal_name": adicao.fornecedor_nome,
                    "street_number": adicao.fornecedor_numero,
                    "street": adicao.fornecedor_logradouro,
                    "city": adicao.fornecedor_cidade,
                }
            )
        vals.update(
            {
                "fornecedor_partner_id": fornecedor_partner_id.id,
            }
        )

        return vals

    def calcular_declaracao(self):
        for record in self:
            valor_deducao = 0

            for x in record.di_adicao_valor_ids:
                if x.valor < 0:
                    valor_deducao += x.valor

            record.valor_outros = (
                record.valor_taxa_siscomex
                + record.valor_taxa_capatazia
                + record.valor_taxa_afrmm
                + abs(valor_deducao)
            )

            for line in record.di_adicao_mercadoria_ids:
                line._compute_totals()
