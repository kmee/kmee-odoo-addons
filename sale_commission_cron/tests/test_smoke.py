# Copyright 2026 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged

MODULE = __name__.split(".")[2]


@tagged("post_install", "-at_install")
class TestModuleSmoke(TransactionCase):
    """Generic checks: the module is installed and its models, views, actions
    and reports can be loaded in the current Odoo series."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        data = cls.env["ir.model.data"].search([("module", "=", MODULE)])
        models = set()
        for rec in data.filtered(lambda r: r.model == "ir.model"):
            model = cls.env["ir.model"].browse(rec.res_id).exists()
            if model:
                models.add(model.model)
        field_ids = [r.res_id for r in data if r.model == "ir.model.fields"]
        models.update(
            cls.env["ir.model.fields"].browse(field_ids).exists().mapped("model")
        )
        cls.model_names = sorted(name for name in models if name in cls.env)
        cls.view_ids = [r.res_id for r in data if r.model == "ir.ui.view"]
        cls.action_ids = [r.res_id for r in data if r.model == "ir.actions.act_window"]
        cls.report_ids = [r.res_id for r in data if r.model == "ir.actions.report"]

    def test_module_is_installed(self):
        module = self.env["ir.module.module"].search([("name", "=", MODULE)])
        self.assertEqual(module.state, "installed")

    def test_models_are_usable(self):
        for name in self.model_names:
            model = self.env[name]
            if model._abstract:
                # abstract helpers may have no fields at all
                continue
            self.assertTrue(model.fields_get(), name)
            if not model._transient:
                model.search([], limit=1)

    def test_views_are_valid(self):
        views = self.env["ir.ui.view"].browse(self.view_ids).exists()
        for view in views:
            if view.type == "qweb" or not view.model or view.model not in self.env:
                continue
            self.env[view.model].get_view(view.id, view.type)

    def test_actions_can_be_read(self):
        for action in (
            self.env["ir.actions.act_window"].browse(self.action_ids).exists()
        ):
            self.assertTrue(action.read(), action.name)

    def test_reports_are_registered(self):
        for report in self.env["ir.actions.report"].browse(self.report_ids).exists():
            self.assertTrue(report.report_name, report.name)
            self.assertTrue(report.model in self.env, report.name)
