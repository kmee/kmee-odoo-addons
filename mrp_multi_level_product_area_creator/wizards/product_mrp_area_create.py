# Copyright 2025 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductMrpAreaCreate(models.TransientModel):

    _name = "product.mrp.area.create"

    product_ids = fields.Many2many("product.product", string="Produtos")
    mrp_area_id = fields.Many2one("mrp.area", string="Área MRP", required=True)

    def _get_all_bom_components_recursive(self, products):
        """
        Retorna todos os componentes das BOMs recursivamente.

        :param products: recordset de product.product
        :return: recordset de product.product com todos os componentes
        """
        all_products = self.env["product.product"]
        processed_products = self.env["product.product"]
        products_to_process = products.filtered(lambda p: p.type == "product")

        level = 0
        while products_to_process:
            level += 1
            _logger.info(
                f"Processando nível {level} - {len(products_to_process)} produtos"
            )

            new_products = self.env["product.product"]

            for product in products_to_process:
                # Evita processar o mesmo produto duas vezes
                if product in processed_products:
                    continue

                # Adiciona ao resultado
                all_products |= product
                processed_products |= product

                # Busca BOM ativa do produto
                bom = self.env["mrp.bom"].search(
                    [
                        ("product_tmpl_id", "=", product.product_tmpl_id.id),
                        ("active", "=", True),
                        "|",
                        ("product_id", "=", False),
                        ("product_id", "=", product.id),
                    ],
                    limit=1,
                )

                if bom:
                    _logger.info(
                        f"  → {product.default_code or product.name}: "
                        f"BOM encontrada com {len(bom.bom_line_ids)} componentes"
                    )
                    # Adiciona componentes para processamento
                    components = bom.bom_line_ids.mapped("product_id").filtered(
                        lambda p: p.type == "product"
                    )
                    new_products |= components

            # Próxima iteração: apenas produtos novos não processados
            products_to_process = new_products - processed_products

        _logger.info(f"Total de produtos encontrados (recursivo): {len(all_products)}")
        return all_products

    def _create_product_mrp_areas(self, products):
        """
        Cria os registros product.mrp.area.

        :param products: recordset de product.product
        :return: recordset de product.mrp.area criados
        """
        product_mrp_area_obj = self.env["product.mrp.area"]
        created_records = self.env["product.mrp.area"]
        existing_count = 0

        for product in products:
            # Verifica se já existe
            existing = product_mrp_area_obj.search(
                [
                    ("product_id", "=", product.id),
                    ("mrp_area_id", "=", self.mrp_area_id.id),
                ],
                limit=1,
            )

            if existing:
                existing_count += 1
                _logger.info(
                    f"  ○ Já existe: {product.default_code or product.name} "
                    f"(ID: {existing.id})"
                )
                continue

            # Cria novo registro
            new_record = product_mrp_area_obj.create(
                {
                    "product_id": product.id,
                    "mrp_area_id": self.mrp_area_id.id,
                    "mrp_applicable": True,
                }
            )
            created_records |= new_record
            _logger.info(
                f"  ✓ Criado: {product.default_code or product.name} "
                f"(ID: {new_record.id})"
            )

        return created_records, existing_count

    def doit(self):
        self.ensure_one()

        if not self.product_ids:
            raise UserError(_("Selecione ao menos um produto!"))

        if not self.mrp_area_id:
            raise UserError(_("Selecione uma Área MRP!"))

        _logger.info("=" * 80)
        _logger.info("INICIANDO CRIAÇÃO DE PRODUCT.MRP.AREA")
        _logger.info(f"Área MRP: {self.mrp_area_id.name}")
        _logger.info(f"Produtos iniciais: {len(self.product_ids)}")
        _logger.info("=" * 80)

        # Determina quais produtos processar
        products_to_create = self._get_all_bom_components_recursive(self.product_ids)

        _logger.info(f"Total de produtos a processar: {len(products_to_create)}")

        # Cria os registros
        created_records, existing_count = self._create_product_mrp_areas(
            products_to_create
        )

        _logger.info("=" * 80)
        _logger.info("PROCESSAMENTO CONCLUÍDO")
        _logger.info(f"  • Criados: {len(created_records)}")
        _logger.info(f"  • Já existiam: {existing_count}")
        _logger.info(f"  • Total processado: {len(products_to_create)}")
        _logger.info("=" * 80)

        # Prepara mensagem de retorno
        message = _(
            "Product MRP Area criados com sucesso!\n\n"
            "• Criados: %(created)s\n"
            "• Já existiam: %(existing)s\n"
            "• Total processado: %(total)s"
        ) % {
            "created": len(created_records),
            "existing": existing_count,
            "total": len(products_to_create),
        }

        # Se criou algum registro, abre a lista
        if created_records:
            action = {
                "type": "ir.actions.act_window",
                "name": _("Product MRP Areas Criados"),
                "res_model": "product.mrp.area",
                "domain": [("id", "in", created_records.ids)],
                "view_mode": "tree,form",
                "context": {"create": False},
            }
        else:
            # Se não criou nada, apenas mostra mensagem
            action = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Informação"),
                    "message": message,
                    "type": "info",
                    "sticky": False,
                },
            }

        return action
