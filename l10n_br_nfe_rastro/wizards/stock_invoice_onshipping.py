# Copyright (C) 2024-Today - KMEE (<http://www.kmee.com.br>).
# @author Diego Paradeda <diego.paradeda@kmee.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models


class StockInvoiceOnshipping(models.TransientModel):
    _inherit = "stock.invoice.onshipping"

    def _get_invoice_line_values(self, moves, invoice_values, invoice):
        """
        Inherited to gather lot data, if present in the picking, and populate the
        nfe40_rastro tag.

        :param moves: stock.move - The stock movements associated with the invoice.
        :param invoice_values: dict - The current values being populated for the invoice.
        :param invoice: account.invoice - The invoice being processed.
        :return: dict - Updated invoice line values including nfe40_rastro data if applicable.
        """

        # Call the super method to get the existing values
        values = super()._get_invoice_line_values(moves, invoice_values, invoice)

        # Initialize nfe40_rastro_dict with operation type 5 to clear existing data
        nfe40_rastro_dict = [(5, 0)]

        # Iterate through the stock move lines
        for sml in moves.mapped("move_line_ids"):
            # Continue to the next iteration if lot_id is not present
            if not sml.lot_id:
                continue

            # Safely extract the production and expiration dates
            dFab = sml.lot_id.production_date and sml.lot_id.production_date.date()
            dVal = sml.lot_id.expiration_date and sml.lot_id.expiration_date.date()

            # Skip if any required tags dFab and dVal are not set
            if not dFab or not dVal:
                continue

            # Create the lot dictionary with required fields
            lot_dict = {
                "nfe40_nLote": sml.lot_id.name,
                "nfe40_qLote": sml.qty_done,
                "nfe40_dFab": dFab,
                "nfe40_dVal": dVal,
                # "nfe40_cAgreg": "", # cAgreg is not yet handled, might be added in the future
            }

            # Append lot data to nfe40_rastro_dict with operation type 0 (create new data)
            nfe40_rastro_dict.append((0, 0, lot_dict))

        # Assign the nfe40_rastro field in the values dictionary
        values["nfe40_rastro"] = nfe40_rastro_dict

        return values
