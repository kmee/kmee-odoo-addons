# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class AccountStatementImportSheetParser(models.TransientModel):
    _inherit = "account.statement.import.sheet.parser"

    def _get_sheet_type(self, data_file):
        """Read as xls the OLE files that guess_mimetype cannot classify.

        Bank exports written by other tools than Excel have no "Microsoft
        Excel" marker, so without libmagic they are taken for msword and the
        19.0 parser refuses them."""
        sheet_type = super()._get_sheet_type(data_file)
        if not sheet_type and data_file.startswith(OLE_SIGNATURE):
            return "xls"
        return sheet_type
