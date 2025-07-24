import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf_prepare_streams(self, data, res_ids):
        return super(IrActionsReport, self)._render_qweb_pdf_prepare_streams(
            data, res_ids
        )

    def _is_sale_order_report(self, report_ref, res_ids):
        try:
            if hasattr(report_ref, "model") and report_ref.model == "sale.order":
                return True

            if isinstance(report_ref, str):
                try:
                    report = self.env.ref(report_ref, raise_if_not_found=False)
                    if (
                        report
                        and hasattr(report, "model")
                        and report.model == "sale.order"
                    ):
                        return True
                except Exception:
                    pass

            if res_ids:
                first_id = res_ids[0] if isinstance(res_ids, list) else res_ids
                try:
                    sale_order = self.env["sale.order"].browse(first_id)
                    if sale_order.exists():
                        return True
                except Exception:
                    pass

            if hasattr(self, "model") and self.model == "sale.order":
                return True

        except Exception as e:
            _logger.error(f"Erro ao verificar se é relatório de sale.order: {e}")

        return False

    def _apply_pdf_merge(self, res_ids, pdf_content):
        """
        Aplica a mesclagem de PDF para os registros de sale.order
        """
        try:
            if isinstance(res_ids, int):
                res_ids = [res_ids]

            cover_record = self.env["sale.order.cover.pdf"].get_active_cover()
            if not cover_record:
                return pdf_content

            for res_id in res_ids:
                sale_order = self.env["sale.order"].browse(res_id)

                if not sale_order.exists():
                    continue

                if sale_order.merge_pdf:
                    merged_pdf = sale_order.merge_with_cover_pdf(pdf_content)
                    return merged_pdf

        except Exception as e:
            _logger.error(f"Erro ao aplicar mesclagem de PDF: {e}")

        return pdf_content

    def _render_qweb_pdf(self, res_ids, data=None):
        pdf_content, report_format = super(IrActionsReport, self)._render_qweb_pdf(
            res_ids, data
        )
        if hasattr(self, "model") and self.model == "sale.order" and res_ids:
            merged_pdf = self._apply_pdf_merge(res_ids, pdf_content)
            if merged_pdf != pdf_content:
                pdf_content = merged_pdf

        return pdf_content, report_format

    @api.model
    def _get_report_from_name(self, report_name):
        """Override para debug e interceptação"""
        result = super(IrActionsReport, self)._get_report_from_name(report_name)
        return result
