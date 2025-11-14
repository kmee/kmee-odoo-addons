from odoo import fields, models


class TestViewItem(models.Model):
    _name = "test.view.item"
    _description = "List of views to test"

    view_xml_id = fields.Char("View XML ID", required=True)

    def run_global_test(self):
        runner = self.env["test.view.runner"].sudo().create({})
        runner.run_view_test(run_global=True)

    def run_all_test(self):
        runner = self.env["test.view.runner"].sudo().create({})
        runner.run_view_test()

    def run_test(self):
        runner = self.env["test.view.runner"].sudo().create({})
        runner.run_view_test(views=self.ids)
